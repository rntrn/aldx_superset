"""Pembangun dashboard Superset dari definisi Python ("dashboard as code").

Definisi dashboard (dataset SQL, chart, tata letak, filter) ditulis di modul
sps_dash_*.py memakai kelas-kelas di bawah, lalu `build()` membuat atau
MEMPERBARUI semuanya di Superset.

Sifat penting:
- Idempoten: UUID dibentuk dari nama (uuid5), jadi menjalankan ulang akan
  memperbarui objek yang sama, bukan membuat duplikat.
- Memakai fungsi impor resmi Superset (import_dataset/import_chart/
  import_dashboard), sama dengan fitur Import di UI.
- Perubahan yang dibuat lewat UI pada objek buatan builder akan TERTIMPA
  saat build dijalankan lagi. Untuk eksperimen, salin dashboard-nya dulu
  (Save as) di UI.
- Hak akses WAJIB: setiap dataset mendapat aturan RLS {{ sps_akses(...) }}
  (lihat sps_akses.py). Dataset.akses menentukan kolom mana yang dipakai.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import Any

UUID_NAMESPACE = uuid.UUID("6f1f9a52-5d0e-4a7e-9a5c-5b3d2a1c0e01")
VERSION = "1.0.0"
GRID_WIDTH = 12


def stable_uuid(*parts: str) -> str:
    """UUID tetap dari nama, supaya build ulang memperbarui objek yang sama."""
    return str(uuid.uuid5(UUID_NAMESPACE, "/".join(parts)))


# --- Definisi -----------------------------------------------------------------
@dataclass
class Metric:
    name: str
    expression: str
    label: str
    d3format: str | None = None


@dataclass
class Dataset:
    """Satu query SQL + metrik.

    akses: kolom hak akses -> dipasang sebagai RLS wajib (lihat sps_akses.py)
        {}                                    data nasional: hanya lingkup "semua"
        {"cabang": "KD_CABANG", ...}          atribut profil -> kolom di dataset
        None                                  data referensi, tanpa pembatasan
    """
    key: str
    sql: str
    columns: list[str]
    metrics: list[Metric] = field(default_factory=list)
    description: str = ""
    akses: dict[str, str] | None = field(default_factory=dict)


@dataclass
class Chart:
    key: str
    title: str
    viz_type: str
    dataset: str           # key Dataset
    params: dict[str, Any]
    width: int = 3         # dari 12 kolom
    height: int = 50       # satuan grid Superset (±8 px)


@dataclass
class Markdown:
    text: str
    height: int = 12


@dataclass
class SelectFilter:
    """Filter pilihan di panel kiri dashboard, diambil dari kolom dataset."""
    key: str
    label: str
    dataset: str
    column: str
    sort_ascending: bool = True
    default_to_first_item: bool = False


@dataclass
class Dashboard:
    key: str
    title: str
    slug: str
    database_name: str
    datasets: list[Dataset]
    charts: list[Chart]
    rows: list[list[str] | Markdown]   # baris berisi key chart, atau Markdown
    filters: list[SelectFilter] = field(default_factory=list)
    css: str = ""
    roles: list[str] = field(default_factory=list)   # kosong = ikut hak akses dataset


# --- Konversi ke format impor Superset ---------------------------------------
def _dataset_config(dash: Dashboard, ds: Dataset, database_uuid: str) -> dict[str, Any]:
    return {
        "table_name": f"{dash.key}__{ds.key}",
        "sql": ds.sql.strip(),
        "schema": None,
        "description": ds.description,
        "uuid": stable_uuid(dash.key, "dataset", ds.key),
        "database_uuid": database_uuid,
        "version": VERSION,
        "filter_select_enabled": True,
        "normalize_columns": False,
        "always_filter_main_dttm": False,
        "columns": [
            {"column_name": c, "is_dttm": False, "is_active": True,
             "groupby": True, "filterable": True, "type": None}
            for c in ds.columns
        ],
        "metrics": [
            {"metric_name": m.name, "expression": m.expression,
             "verbose_name": m.label, "d3format": m.d3format, "metric_type": None}
            for m in ds.metrics
        ],
    }


def _chart_config(dash: Dashboard, chart: Chart) -> dict[str, Any]:
    return {
        "slice_name": chart.title,
        "viz_type": chart.viz_type,
        "params": {"viz_type": chart.viz_type, "adhoc_filters": [], **chart.params},
        "uuid": stable_uuid(dash.key, "chart", chart.key),
        "dataset_uuid": stable_uuid(dash.key, "dataset", chart.dataset),
        "version": VERSION,
        "query_context": None,
        "cache_timeout": None,
    }


def _position(dash: Dashboard) -> dict[str, Any]:
    """Susun tata letak grid (format posisi v2 Superset)."""
    charts = {c.key: c for c in dash.charts}
    position: dict[str, Any] = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [], "parents": ["ROOT_ID"]},
        "HEADER_ID": {"type": "HEADER", "id": "HEADER_ID", "meta": {"text": dash.title}},
    }
    placeholder_id = 0
    for row_no, row in enumerate(dash.rows, start=1):
        row_id = f"ROW-{row_no}"
        position["GRID_ID"]["children"].append(row_id)
        position[row_id] = {"type": "ROW", "id": row_id, "children": [],
                            "parents": ["ROOT_ID", "GRID_ID"],
                            "meta": {"background": "BACKGROUND_TRANSPARENT"}}
        parents = ["ROOT_ID", "GRID_ID", row_id]

        if isinstance(row, Markdown):
            item_id = f"MARKDOWN-{row_no}"
            position[item_id] = {"type": "MARKDOWN", "id": item_id, "children": [],
                                 "parents": parents,
                                 "meta": {"width": GRID_WIDTH, "height": row.height,
                                          "code": row.text}}
            position[row_id]["children"].append(item_id)
            continue

        if sum(charts[k].width for k in row) > GRID_WIDTH:
            raise ValueError(f"Baris {row_no} lebih lebar dari {GRID_WIDTH} kolom: {row}")
        for key in row:
            chart = charts[key]
            placeholder_id += 1
            item_id = f"CHART-{key}"
            position[item_id] = {"type": "CHART", "id": item_id, "children": [],
                                 "parents": parents,
                                 "meta": {"width": chart.width, "height": chart.height,
                                          "chartId": placeholder_id,
                                          "uuid": stable_uuid(dash.key, "chart", key),
                                          "sliceName": chart.title}}
            position[row_id]["children"].append(item_id)
    return position


def _native_filter(dash: Dashboard, flt: SelectFilter) -> dict[str, Any]:
    return {
        "id": f"NATIVE_FILTER-{flt.key}",
        "name": flt.label,
        "filterType": "filter_select",
        "type": "NATIVE_FILTER",
        "description": "",
        "targets": [{"datasetUuid": stable_uuid(dash.key, "dataset", flt.dataset),
                     "column": {"name": flt.column}}],
        "controlValues": {
            "multiSelect": False,
            "enableEmptyFilter": False,
            "defaultToFirstItem": flt.default_to_first_item,
            "inverseSelection": False,
            "searchAllOptions": False,
            "sortAscending": flt.sort_ascending,
        },
        "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
        "cascadeParentIds": [],
        "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
    }


def _dashboard_config(dash: Dashboard) -> dict[str, Any]:
    return {
        "dashboard_title": dash.title,
        "slug": dash.slug,
        "uuid": stable_uuid(dash.key, "dashboard"),
        "version": VERSION,
        "css": dash.css,
        "published": True,
        "position": _position(dash),
        "metadata": {
            "native_filter_configuration": [_native_filter(dash, f) for f in dash.filters],
            "global_chart_configuration": {"scope": {"rootPath": ["ROOT_ID"], "excluded": []},
                                           "chartsInScope": []},
            "chart_configuration": {},
            "cross_filters_enabled": False,
            "color_scheme": "",
            "refresh_frequency": 0,
            "expanded_slices": {},
            "label_colors": {},
            "timed_refresh_immune_slices": [],
            "default_filters": "{}",
        },
    }


def _validate(dash: Dashboard) -> None:
    """Periksa referensi antar-bagian sebelum menyentuh database."""
    dataset_keys = {d.key for d in dash.datasets}
    chart_keys = {c.key for c in dash.charts}
    for chart in dash.charts:
        if chart.dataset not in dataset_keys:
            raise ValueError(f"Chart '{chart.key}' memakai dataset tak dikenal '{chart.dataset}'")
    for flt in dash.filters:
        if flt.dataset not in dataset_keys:
            raise ValueError(f"Filter '{flt.key}' memakai dataset tak dikenal '{flt.dataset}'")
    for row in dash.rows:
        if not isinstance(row, Markdown):
            missing = [k for k in row if k not in chart_keys]
            if missing:
                raise ValueError(f"Tata letak memakai chart tak dikenal: {missing}")


def rls_clause(akses: dict[str, str]) -> str:
    """Klausa RLS untuk satu dataset, mis. {{ sps_akses(cabang='KD_CABANG') }}."""
    args = ", ".join(f"{atribut}='{kolom}'" for atribut, kolom in sorted(akses.items()))
    return "{{ sps_akses(" + args + ") }}"


def _sync_rls(table, ds: Dataset) -> None:
    """Pasang/perbarui/hapus aturan RLS wajib untuk satu dataset."""
    from superset import db
    from superset.connectors.sqla.models import RowLevelSecurityFilter
    from superset.utils.core import RowLevelSecurityFilterType

    name = f"akses__{table.table_name}"
    rls = db.session.query(RowLevelSecurityFilter).filter_by(name=name).one_or_none()
    if ds.akses is None:
        if rls is not None:
            db.session.delete(rls)
        return
    rls = rls or RowLevelSecurityFilter(name=name)
    rls.description = "Dibuat otomatis oleh sps_dashboard_builder (hak akses wajib)."
    rls.filter_type = RowLevelSecurityFilterType.BASE   # Base tanpa role = berlaku untuk SEMUA user
    rls.roles = []
    rls.tables = [table]
    rls.clause = rls_clause(ds.akses)
    db.session.add(rls)


ROLE_PEMBACA_DATASET = [os.environ.get("SPS_ROLE_PENGGUNA") or "Pengguna"]  # baca dataset (baris tetap dibatasi RLS)


def _beri_akses_dataset(table) -> None:
    """Role pengguna boleh memakai dataset (Asisten AI / Auto Chart); RLS tetap membatasi baris."""
    from superset import security_manager as sm

    pv = sm.add_permission_view_menu("datasource_access", table.get_perm())
    for nama in ROLE_PEMBACA_DATASET:
        role = sm.add_role(nama)
        if pv not in role.permissions:
            sm.add_permission_role(role, pv)


# --- Build --------------------------------------------------------------------
def build(dash: Dashboard, owner_username: str = "admin") -> str:
    """Buat/perbarui dashboard di Superset. Mengembalikan URL relatifnya."""
    from superset import db, security_manager
    from superset.charts.schemas import ImportV1ChartSchema
    from superset.commands.chart.importers.v1.utils import import_chart
    from superset.commands.dashboard.importers.v1.utils import import_dashboard, update_id_refs
    from superset.commands.dataset.importers.v1.utils import import_dataset
    from superset.commands.utils import update_chart_config_dataset
    from superset.dashboards.schemas import ImportV1DashboardSchema
    from superset.datasets.schemas import ImportV1DatasetSchema
    from superset.models.core import Database
    from superset.models.slice import Slice
    from superset.utils.core import override_user

    _validate(dash)

    owner = security_manager.find_user(username=owner_username)
    if owner is None:
        raise RuntimeError(f"User '{owner_username}' tidak ada di Superset")

    database = db.session.query(Database).filter_by(database_name=dash.database_name).one_or_none()
    if database is None:
        raise RuntimeError(
            f"Koneksi '{dash.database_name}' belum ada. Buat lewat Pusat Kendali > Hubungkan data dulu."
        )

    with override_user(owner):
        dataset_info: dict[str, dict[str, Any]] = {}
        for ds in dash.datasets:
            config = _dataset_config(dash, ds, str(database.uuid))
            ImportV1DatasetSchema().load(config)            # validasi format
            config["database_id"] = database.id
            table = import_dataset(config, overwrite=True)
            _sync_rls(table, ds)
            _beri_akses_dataset(table)
            dataset_info[config["uuid"]] = {"datasource_id": table.id,
                                            "datasource_type": table.datasource_type,
                                            "datasource_name": table.table_name}
            print(f"  dataset  {table.table_name}")

        chart_ids: dict[str, int] = {}
        for chart in dash.charts:
            config = _chart_config(dash, chart)
            ImportV1ChartSchema().load(config)
            config = update_chart_config_dataset(config, dataset_info[config["dataset_uuid"]])
            slc = import_chart(config, overwrite=True)
            chart_ids[config["uuid"]] = slc.id
            print(f"  chart    {chart.title}")

        config = _dashboard_config(dash)
        ImportV1DashboardSchema().load(config)
        config = update_id_refs(config, chart_ids, dataset_info)
        dashboard = import_dashboard(config, overwrite=True)
        dashboard.slices = db.session.query(Slice).filter(Slice.id.in_(chart_ids.values())).all()
        dashboard.roles = [security_manager.add_role(r) for r in dash.roles]
        db.session.commit()
        print(f"  dashboard {dash.title}")

    return f"/superset/dashboard/{dash.slug}/"

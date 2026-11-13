"""Membaca pengaturan asisten AI dari config/ai.yaml (+ API key dari .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

AI_YAML = Path(os.environ.get("AI_CONFIG") or Path(__file__).resolve().parent.parent / "ai.yaml")


@dataclass(frozen=True)
class ModelAI:
    id: str
    nama: str
    base_url: str
    model: str
    api_key: str           # kosong untuk model lokal
    kirim_data: bool

    @property
    def publik(self) -> dict:
        """Info yang aman ditampilkan ke browser (tanpa key/alamat)."""
        return {"id": self.id, "nama": self.nama, "kirim_data": self.kirim_data}


@dataclass(frozen=True)
class Pengaturan:
    model: list[ModelAI]
    bawaan: str
    peran_boleh: list[str]
    langkah_maks: int
    baris_maks: int
    baris_ke_model: int
    batas_detik_model: int
    batas_detik_lokal: int = 240
    batas_latar: int = 900          # detik total satu pertanyaan di latar belakang (tidak terikat timeout web)

    def batas_untuk(self, model: "ModelAI") -> int:
        """Model lokal (tanpa key, sering di CPU) diberi waktu lebih lama daripada layanan cloud."""
        return self.batas_detik_model if model.api_key else max(self.batas_detik_model, self.batas_detik_lokal)

    def cari_model(self, model_id: str | None) -> ModelAI:
        for m in self.model:
            if m.id == (model_id or self.bawaan):
                return m
        if not self.model:
            raise LookupError("Belum ada model AI yang aktif. Periksa config/ai.yaml dan .env.")
        return self.model[0]


def baca_yaml() -> dict:
    with AI_YAML.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def sumber_lokal(data: dict | None = None) -> list[dict]:
    """Server model lokal yang diperiksa otomatis (ai.yaml: temukan_lokal)."""
    data = baca_yaml() if data is None else data
    return [{"nama": str(s["nama"]), "base_url": str(s["base_url"]).rstrip("/")}
            for s in data.get("temukan_lokal") or [] if s.get("base_url")]


def muat(hanya_aktif: bool = True) -> Pengaturan:
    """Dibaca ulang setiap permintaan, jadi perubahan ai.yaml langsung berlaku.

    hanya_aktif: hanya model yang servernya menjawab (sps_ai/status.py, disimpan 60 detik),
                 ditambah model lokal yang ditemukan otomatis (temukan_lokal).
    API key: dari .env, atau yang diisi Admin lewat aplikasi (sps_ai/kunci_api.py).
    """
    data = baca_yaml()

    from sps_ai import kunci_api
    tersimpan = kunci_api.semua()            # key cloud & model bawaan yang diisi lewat aplikasi

    aktif = []
    for m in data.get("model") or []:
        key_env = (m.get("api_key_env") or "").strip()
        api_key = (os.environ.get(key_env, "").strip() or tersimpan.get(key_env, "")) if key_env else ""
        if key_env and not api_key:
            continue                                   # butuh key tapi belum diisi
        aktif.append(ModelAI(
            id=str(m["id"]), nama=str(m.get("nama", m["id"])),
            base_url=str(m["base_url"]).rstrip("/"), model=str(m["model"]),
            api_key=api_key, kirim_data=bool(m.get("kirim_data", False)),
        ))
    if hanya_aktif:
        from sps_ai import status
        aktif = status.aktif(aktif) if aktif else []
        # Model lokal yang ditemukan otomatis (semua model chat yang sudah diunduh di Ollama, LM Studio, ...).
        sudah = {(m.base_url, m.model.lower()) for m in aktif}
        temuan = []
        for srv in status.temukan(sumber_lokal(data)):
            for nama in srv["model"]:
                if (srv["base_url"], nama.lower()) in sudah:
                    continue
                temuan.append(ModelAI(id=f"lokal:{srv['nama']}:{nama}", nama=f"{nama} — lokal ({srv['nama']})",
                                      base_url=srv["base_url"], model=nama, api_key="", kirim_data=True))
        lokal = [m for m in aktif if not m.api_key]
        aktif = lokal + temuan + [m for m in aktif if m.api_key]
    return Pengaturan(
        model=aktif,
        bawaan=tersimpan.get(kunci_api.BAWAAN) or str(data.get("bawaan", "")),
        peran_boleh=[str(p).replace("{role_pengguna}", os.environ.get("SPS_ROLE_PENGGUNA") or "Pengguna")
                     for p in data.get("peran_boleh") or []],
        langkah_maks=int(data.get("langkah_maks", 6)),
        baris_maks=int(data.get("baris_maks", 500)),
        baris_ke_model=int(data.get("baris_ke_model", 50)),
        batas_detik_model=int(data.get("batas_detik_model", 120)),
        batas_detik_lokal=int(data.get("batas_detik_lokal", 240)),
        batas_latar=max(60, min(int(data.get("batas_latar_detik", 900)), 3600)),
    )

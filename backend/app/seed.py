import os
from pathlib import Path

from backend.app.services.ingest_service import ingest_document

DATA_DIR = Path(__file__).resolve().parents[1].parent / 'data'
# adjust: data folder is at repo root /data
DATA_DIR = Path(os.getcwd()) / 'data'


def seed_all():
    for md in DATA_DIR.glob('*.md'):
        title = md.stem
        content = md.read_text(encoding='utf-8')
        print(f'Ingesting {md.name}...')
        n = ingest_document(title, content, metadata={"source": str(md)})
        print(f'Indexed {n} chunks for {title}')


if __name__ == '__main__':
    seed_all()

import random
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Ensure project root is on sys.path when running from scripts/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app  # ensures extensions and mongo are initialized
from extensions import mongo_db


def upsert(collection_name, query, data):
    mongo_db[collection_name].update_one(query, {"$set": data}, upsert=True)


def seed_hierarchy():
    # Central
    upsert(
        "centrais",
        {"id": 1},
        {
            "id": 1,
            "nome": "Central Hospitalar",
        },
    )

    # Almoxarifado
    upsert(
        "almoxarifados",
        {"id": 1},
        {
            "id": 1,
            "nome": "Almox Principal",
            "central_id": 1,
        },
    )

    # Sub-almoxarifado
    upsert(
        "sub_almoxarifados",
        {"id": 1},
        {
            "id": 1,
            "nome": "Sub-Almox Norte",
            "almoxarifado_id": 1,
            "central_id": 1,
        },
    )

    # Setor
    upsert(
        "setores",
        {"id": 1},
        {
            "id": 1,
            "nome": "UTI Adulto",
            "sub_almoxarifado_id": 1,
            "almoxarifado_id": 1,
            "central_id": 1,
        },
    )


def seed_produtos():
    produtos = [
        {
            "id": 1,
            "nome": "Máscara N95",
            "codigo": "MASK-N95",
            "unidade_medida": "un",
            "estoque_minimo": 50,
        },
        {
            "id": 2,
            "nome": "Seringa 5ml",
            "codigo": "SER-5ML",
            "unidade_medida": "un",
            "estoque_minimo": 200,
        },
    ]

    for p in produtos:
        upsert("produtos", {"id": p["id"]}, p)


def seed_estoques():
    # Low stock for product 1 at Almoxarifado
    upsert(
        "estoque",
        {"produto_id": 1, "local_tipo": "almoxarifado", "local_id": 1},
        {
            "produto_id": 1,
            "quantidade": 35,
            "quantidade_disponivel": 30,
            "local_tipo": "almoxarifado",
            "local_id": 1,
            "almoxarifado_id": 1,
            "sub_almoxarifado_id": None,
            "setor_id": None,
            "central_id": 1,
        },
    )

    # Adequate stock for product 2 (won't show in low-stock)
    upsert(
        "estoque",
        {"produto_id": 2, "local_tipo": "almoxarifado", "local_id": 1},
        {
            "produto_id": 2,
            "quantidade": 500,
            "quantidade_disponivel": 480,
            "local_tipo": "almoxarifado",
            "local_id": 1,
            "almoxarifado_id": 1,
            "sub_almoxarifado_id": None,
            "setor_id": None,
            "central_id": 1,
        },
    )


def seed_movimentacoes():
    # Generate 30 days of movements for product 1 from almoxarifado to setor
    base_date = datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
    movimentos = []
    for i in range(30):
        day = base_date - timedelta(days=i)
        quantidade = random.randint(1, 6)
        movimentos.append(
            {
                "id": f"mov-{day.strftime('%Y%m%d')}-p1",
                "produto_id": 1,
                "tipo": "saida",
                "quantidade": quantidade,
                "data_movimentacao": day,
                "origem_tipo": "almoxarifado",
                "origem_id": 1,
                "destino_tipo": "setor",
                "destino_id": 1,
                "almoxarifado_id": 1,
                "sub_almoxarifado_id": 1,
                "setor_id": 1,
                "central_id": 1,
                "usuario_id": None,
            }
        )

    # A few movements for product 2 (less frequent)
    for i in range(0, 30, 5):
        day = base_date - timedelta(days=i)
        movimentos.append(
            {
                "id": f"mov-{day.strftime('%Y%m%d')}-p2",
                "produto_id": 2,
                "tipo": "saida",
                "quantidade": random.randint(2, 10),
                "data_movimentacao": day,
                "origem_tipo": "almoxarifado",
                "origem_id": 1,
                "destino_tipo": "setor",
                "destino_id": 1,
                "almoxarifado_id": 1,
                "sub_almoxarifado_id": 1,
                "setor_id": 1,
                "central_id": 1,
                "usuario_id": None,
            }
        )

    # Upsert movements (use unique id to avoid duplicates on re-run)
    for m in movimentos:
        mongo_db["movimentacoes"].update_one({"id": m["id"]}, {"$set": m}, upsert=True)


def main():
    with app.app_context():
        seed_hierarchy()
        seed_produtos()
        seed_estoques()
        seed_movimentacoes()
        print("Seed demo concluído: hierarquia, produtos, estoques e movimentações populados.")


if __name__ == "__main__":
    main()
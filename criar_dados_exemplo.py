#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para criar dados de exemplo no sistema VitaFlow
Hospital Municipal de Angicos
"""

from app import app, db, Item
from datetime import datetime, timedelta
import random

def criar_dados_exemplo():
    """Cria dados de exemplo para testar o sistema"""
    
    with app.app_context():
        # Limpar dados existentes
        Item.query.delete()
        db.session.commit()
        
        # Lista de itens de exemplo
        itens_exemplo = [
            # Enfermagem - Almoxarifado
            {
                'nome': 'Seringa 10ml',
                'setor': 'enfermagem',
                'localizacao': 'almoxarifado',
                'quantidade': 150,
                'data_compra': datetime.now() - timedelta(days=30),
                'data_vencimento': datetime.now() + timedelta(days=365),
                'preco_unitario': 2.50,
                'lote': 'SER001',
                'fornecedor': 'MedSupply Ltda',
                'descricao': 'Seringa descartável 10ml com agulha'
            },
            {
                'nome': 'Luvas de Procedimento',
                'setor': 'enfermagem',
                'localizacao': 'almoxarifado',
                'quantidade': 5,  # Estoque baixo
                'data_compra': datetime.now() - timedelta(days=15),
                'data_vencimento': datetime.now() + timedelta(days=730),
                'preco_unitario': 0.85,
                'lote': 'LUV002',
                'fornecedor': 'ProMed Distribuidora',
                'descricao': 'Luvas de látex tamanho M'
            },
            {
                'nome': 'Gaze Estéril',
                'setor': 'enfermagem',
                'localizacao': 'almoxarifado',
                'quantidade': 0,  # Estoque zerado
                'data_compra': datetime.now() - timedelta(days=60),
                'data_vencimento': datetime.now() + timedelta(days=180),
                'preco_unitario': 1.20,
                'lote': 'GAZ003',
                'fornecedor': 'Cirúrgica Brasil',
                'descricao': 'Gaze estéril 7,5x7,5cm'
            },
            
            # Farmácia - Medicamentos
            {
                'nome': 'Dipirona 500mg',
                'setor': 'farmacia',
                'localizacao': 'farmacia',
                'quantidade': 200,
                'data_compra': datetime.now() - timedelta(days=45),
                'data_vencimento': datetime.now() + timedelta(days=90),  # Próximo ao vencimento
                'preco_unitario': 0.15,
                'lote': 'DIP004',
                'fornecedor': 'Farmacêutica Nacional',
                'descricao': 'Dipirona sódica 500mg comprimido'
            },
            {
                'nome': 'Paracetamol 750mg',
                'setor': 'farmacia',
                'localizacao': 'farmacia',
                'quantidade': 80,
                'data_compra': datetime.now() - timedelta(days=20),
                'data_vencimento': datetime.now() + timedelta(days=540),
                'preco_unitario': 0.25,
                'lote': 'PAR005',
                'fornecedor': 'Laboratório Vida',
                'descricao': 'Paracetamol 750mg comprimido'
            },
            {
                'nome': 'Soro Fisiológico 500ml',
                'setor': 'farmacia',
                'localizacao': 'almoxarifado',
                'quantidade': 25,
                'data_compra': datetime.now() - timedelta(days=10),
                'data_vencimento': datetime.now() + timedelta(days=1095),
                'preco_unitario': 3.80,
                'lote': 'SOR006',
                'fornecedor': 'Soluções Médicas',
                'descricao': 'Soro fisiológico 0,9% 500ml'
            },
            
            # Laboratório
            {
                'nome': 'Tubo de Ensaio',
                'setor': 'laboratorio',
                'localizacao': 'almoxarifado',
                'quantidade': 300,
                'data_compra': datetime.now() - timedelta(days=5),
                'data_vencimento': None,  # Sem data de vencimento
                'preco_unitario': 1.50,
                'lote': 'TUB007',
                'fornecedor': 'LabEquip',
                'descricao': 'Tubo de ensaio 15ml com tampa'
            },
            {
                'nome': 'Reagente Glicose',
                'setor': 'laboratorio',
                'localizacao': 'farmacia',
                'quantidade': 12,
                'data_compra': datetime.now() - timedelta(days=90),
                'data_vencimento': datetime.now() - timedelta(days=10),  # Vencido
                'preco_unitario': 45.00,
                'lote': 'REA008',
                'fornecedor': 'BioLab Reagentes',
                'descricao': 'Reagente para dosagem de glicose'
            },
            
            # Centro Cirúrgico
            {
                'nome': 'Bisturi Descartável',
                'setor': 'centro_cirurgico',
                'localizacao': 'almoxarifado',
                'quantidade': 50,
                'data_compra': datetime.now() - timedelta(days=25),
                'data_vencimento': datetime.now() + timedelta(days=1460),
                'preco_unitario': 8.90,
                'lote': 'BIS009',
                'fornecedor': 'Cirúrgica Especializada',
                'descricao': 'Bisturi descartável nº 15'
            },
            {
                'nome': 'Fio de Sutura',
                'setor': 'centro_cirurgico',
                'localizacao': 'farmacia',
                'quantidade': 3,  # Estoque baixo
                'data_compra': datetime.now() - timedelta(days=40),
                'data_vencimento': datetime.now() + timedelta(days=20),  # Próximo ao vencimento
                'preco_unitario': 12.50,
                'lote': 'FIO010',
                'fornecedor': 'Sutura Brasil',
                'descricao': 'Fio de sutura absorvível 3-0'
            },
            
            # Itens adicionais para teste
            {
                'nome': 'Álcool 70%',
                'setor': 'enfermagem',
                'localizacao': 'farmacia',
                'quantidade': 45,
                'data_compra': datetime.now() - timedelta(days=12),
                'data_vencimento': datetime.now() + timedelta(days=365),
                'preco_unitario': 4.20,
                'lote': 'ALC011',
                'fornecedor': 'Química Hospitalar',
                'descricao': 'Álcool etílico 70% - 1 litro'
            },
            {
                'nome': 'Termômetro Digital',
                'setor': 'enfermagem',
                'localizacao': 'almoxarifado',
                'quantidade': 8,
                'data_compra': datetime.now() - timedelta(days=180),
                'data_vencimento': None,
                'preco_unitario': 25.90,
                'lote': 'TER012',
                'fornecedor': 'Equipamentos Médicos',
                'descricao': 'Termômetro digital clínico'
            }
        ]
        
        # Inserir itens no banco de dados
        for item_data in itens_exemplo:
            item = Item(**item_data)
            db.session.add(item)
        
        # Confirmar as alterações
        db.session.commit()
        
        print(f"✅ {len(itens_exemplo)} itens de exemplo criados com sucesso!")
        print("\n📊 Resumo dos dados criados:")
        
        # Estatísticas
        total_itens = Item.query.count()
        almoxarifado_count = Item.query.filter_by(localizacao='almoxarifado').count()
        farmacia_count = Item.query.filter_by(localizacao='farmacia').count()
        
        # Itens por setor
        enfermagem_count = Item.query.filter_by(setor='enfermagem').count()
        farmacia_setor_count = Item.query.filter_by(setor='farmacia').count()
        laboratorio_count = Item.query.filter_by(setor='laboratorio').count()
        centro_cirurgico_count = Item.query.filter_by(setor='centro_cirurgico').count()
        
        # Itens com problemas
        vencidos = Item.query.filter(Item.data_vencimento < datetime.now().date()).count()
        estoque_baixo = Item.query.filter(Item.quantidade <= 5).count()
        estoque_zero = Item.query.filter(Item.quantidade == 0).count()
        
        print(f"   📦 Total de itens: {total_itens}")
        print(f"   🏪 Almoxarifado: {almoxarifado_count} itens")
        print(f"   💊 Farmácia: {farmacia_count} itens")
        print(f"")
        print(f"   👩‍⚕️ Enfermagem: {enfermagem_count} itens")
        print(f"   💉 Farmácia (setor): {farmacia_setor_count} itens")
        print(f"   🔬 Laboratório: {laboratorio_count} itens")
        print(f"   🏥 Centro Cirúrgico: {centro_cirurgico_count} itens")
        print(f"")
        print(f"   ⚠️ Itens vencidos: {vencidos}")
        print(f"   📉 Estoque baixo (≤5): {estoque_baixo}")
        print(f"   🚫 Estoque zerado: {estoque_zero}")
        print(f"")
        print("🌐 Acesse http://127.0.0.1:5000 para testar a aplicação!")

if __name__ == '__main__':
    criar_dados_exemplo()
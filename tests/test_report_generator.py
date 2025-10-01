"""
Gerador de relatórios de teste personalizado
"""
import json
import os
import datetime
from pathlib import Path


class TestReportGenerator:
    """Classe para gerar relatórios de teste personalizados"""
    
    def __init__(self, output_dir="test_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.report_data = {
            'timestamp': datetime.datetime.now().isoformat(),
            'summary': {},
            'test_results': [],
            'coverage': {},
            'performance': {},
            'errors': []
        }
    
    def add_test_result(self, test_name, status, duration=None, error_message=None):
        """Adicionar resultado de teste"""
        result = {
            'test_name': test_name,
            'status': status,  # 'passed', 'failed', 'skipped'
            'duration': duration,
            'error_message': error_message,
            'timestamp': datetime.datetime.now().isoformat()
        }
        self.report_data['test_results'].append(result)
    
    def set_summary(self, total_tests, passed, failed, skipped, duration):
        """Definir resumo dos testes"""
        self.report_data['summary'] = {
            'total_tests': total_tests,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'success_rate': (passed / total_tests * 100) if total_tests > 0 else 0,
            'total_duration': duration
        }
    
    def set_coverage_data(self, coverage_data):
        """Definir dados de cobertura"""
        self.report_data['coverage'] = coverage_data
    
    def add_performance_metric(self, metric_name, value, unit='ms'):
        """Adicionar métrica de performance"""
        self.report_data['performance'][metric_name] = {
            'value': value,
            'unit': unit
        }
    
    def add_error(self, error_type, message, details=None):
        """Adicionar erro encontrado"""
        error = {
            'type': error_type,
            'message': message,
            'details': details,
            'timestamp': datetime.datetime.now().isoformat()
        }
        self.report_data['errors'].append(error)
    
    def generate_json_report(self, filename="test_report.json"):
        """Gerar relatório em formato JSON"""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.report_data, f, indent=2, ensure_ascii=False)
        return filepath
    
    def generate_html_report(self, filename="test_report.html"):
        """Gerar relatório em formato HTML"""
        filepath = self.output_dir / filename
        
        html_content = self._generate_html_content()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def _generate_html_content(self):
        """Gerar conteúdo HTML do relatório"""
        summary = self.report_data['summary']
        
        html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Testes - Almox SMS</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .metric {{
            text-align: center;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .passed {{ color: #28a745; }}
        .failed {{ color: #dc3545; }}
        .skipped {{ color: #ffc107; }}
        .success-rate {{ color: #17a2b8; }}
        .section {{
            padding: 30px;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .test-grid {{
            display: grid;
            gap: 10px;
        }}
        .test-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 5px;
            border-left: 4px solid #ddd;
        }}
        .test-item.passed {{
            border-left-color: #28a745;
        }}
        .test-item.failed {{
            border-left-color: #dc3545;
        }}
        .test-item.skipped {{
            border-left-color: #ffc107;
        }}
        .test-name {{
            font-weight: 500;
        }}
        .test-status {{
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .status-passed {{
            background: #d4edda;
            color: #155724;
        }}
        .status-failed {{
            background: #f8d7da;
            color: #721c24;
        }}
        .status-skipped {{
            background: #fff3cd;
            color: #856404;
        }}
        .error-message {{
            margin-top: 10px;
            padding: 10px;
            background: #f8d7da;
            border-radius: 5px;
            font-family: monospace;
            font-size: 0.9em;
            color: #721c24;
        }}
        .coverage-bar {{
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .coverage-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.3s ease;
        }}
        .performance-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}
        .performance-item {{
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            text-align: center;
        }}
        .footer {{
            background: #343a40;
            color: white;
            text-align: center;
            padding: 20px;
        }}
        @media (max-width: 768px) {{
            .summary {{
                grid-template-columns: 1fr;
            }}
            .performance-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Relatório de Testes</h1>
            <p>Sistema de Almoxarifado SMS</p>
            <p>Gerado em: {self.report_data['timestamp']}</p>
        </div>
        
        <div class="summary">
            <div class="metric">
                <div class="metric-value">{summary.get('total_tests', 0)}</div>
                <div class="metric-label">Total de Testes</div>
            </div>
            <div class="metric">
                <div class="metric-value passed">{summary.get('passed', 0)}</div>
                <div class="metric-label">Aprovados</div>
            </div>
            <div class="metric">
                <div class="metric-value failed">{summary.get('failed', 0)}</div>
                <div class="metric-label">Falharam</div>
            </div>
            <div class="metric">
                <div class="metric-value skipped">{summary.get('skipped', 0)}</div>
                <div class="metric-label">Ignorados</div>
            </div>
            <div class="metric">
                <div class="metric-value success-rate">{summary.get('success_rate', 0):.1f}%</div>
                <div class="metric-label">Taxa de Sucesso</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Resultados dos Testes</h2>
            <div class="test-grid">
        """
        
        # Adicionar resultados dos testes
        for test in self.report_data['test_results']:
            status_class = test['status']
            html += f"""
                <div class="test-item {status_class}">
                    <div>
                        <div class="test-name">{test['test_name']}</div>
                        {f'<div class="error-message">{test["error_message"]}</div>' if test.get('error_message') else ''}
                    </div>
                    <div class="test-status status-{status_class}">{test['status']}</div>
                </div>
            """
        
        html += """
            </div>
        </div>
        """
        
        # Seção de cobertura
        coverage = self.report_data.get('coverage', {})
        if coverage:
            html += f"""
        <div class="section">
            <h2>Cobertura de Código</h2>
            <div class="coverage-bar">
                <div class="coverage-fill" style="width: {coverage.get('percent', 0)}%"></div>
            </div>
            <p>Cobertura: {coverage.get('percent', 0):.1f}% ({coverage.get('covered_lines', 0)}/{coverage.get('total_lines', 0)} linhas)</p>
        </div>
            """
        
        # Seção de performance
        performance = self.report_data.get('performance', {})
        if performance:
            html += """
        <div class="section">
            <h2>Métricas de Performance</h2>
            <div class="performance-grid">
            """
            
            for metric_name, metric_data in performance.items():
                html += f"""
                <div class="performance-item">
                    <h3>{metric_name}</h3>
                    <div class="metric-value">{metric_data['value']}</div>
                    <div class="metric-label">{metric_data['unit']}</div>
                </div>
                """
            
            html += """
            </div>
        </div>
            """
        
        # Seção de erros
        errors = self.report_data.get('errors', [])
        if errors:
            html += """
        <div class="section">
            <h2>Erros Encontrados</h2>
            """
            
            for error in errors:
                html += f"""
                <div class="test-item failed">
                    <div>
                        <div class="test-name">{error['type']}: {error['message']}</div>
                        {f'<div class="error-message">{error["details"]}</div>' if error.get('details') else ''}
                    </div>
                </div>
                """
            
            html += """
        </div>
            """
        
        html += f"""
        <div class="footer">
            <p>&copy; 2024 Sistema de Almoxarifado SMS - Relatório gerado automaticamente</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    def generate_markdown_report(self, filename="test_report.md"):
        """Gerar relatório em formato Markdown"""
        filepath = self.output_dir / filename
        
        summary = self.report_data['summary']
        
        markdown = f"""# Relatório de Testes - Sistema Almoxarifado SMS

**Gerado em:** {self.report_data['timestamp']}

## Resumo

| Métrica | Valor |
|---------|-------|
| Total de Testes | {summary.get('total_tests', 0)} |
| Aprovados | {summary.get('passed', 0)} |
| Falharam | {summary.get('failed', 0)} |
| Ignorados | {summary.get('skipped', 0)} |
| Taxa de Sucesso | {summary.get('success_rate', 0):.1f}% |
| Duração Total | {summary.get('total_duration', 0):.2f}s |

## Resultados dos Testes

"""
        
        # Adicionar resultados dos testes
        for test in self.report_data['test_results']:
            status_emoji = {
                'passed': '✅',
                'failed': '❌',
                'skipped': '⏭️'
            }.get(test['status'], '❓')
            
            markdown += f"### {status_emoji} {test['test_name']}\n\n"
            markdown += f"**Status:** {test['status']}\n\n"
            
            if test.get('duration'):
                markdown += f"**Duração:** {test['duration']:.3f}s\n\n"
            
            if test.get('error_message'):
                markdown += f"**Erro:**\n```\n{test['error_message']}\n```\n\n"
        
        # Seção de cobertura
        coverage = self.report_data.get('coverage', {})
        if coverage:
            markdown += f"""## Cobertura de Código

- **Percentual:** {coverage.get('percent', 0):.1f}%
- **Linhas Cobertas:** {coverage.get('covered_lines', 0)}
- **Total de Linhas:** {coverage.get('total_lines', 0)}

"""
        
        # Seção de performance
        performance = self.report_data.get('performance', {})
        if performance:
            markdown += "## Métricas de Performance\n\n"
            
            for metric_name, metric_data in performance.items():
                markdown += f"- **{metric_name}:** {metric_data['value']} {metric_data['unit']}\n"
            
            markdown += "\n"
        
        # Seção de erros
        errors = self.report_data.get('errors', [])
        if errors:
            markdown += "## Erros Encontrados\n\n"
            
            for error in errors:
                markdown += f"### ❌ {error['type']}\n\n"
                markdown += f"**Mensagem:** {error['message']}\n\n"
                
                if error.get('details'):
                    markdown += f"**Detalhes:**\n```\n{error['details']}\n```\n\n"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        return filepath
    
    def generate_all_reports(self):
        """Gerar todos os tipos de relatório"""
        reports = {}
        reports['json'] = self.generate_json_report()
        reports['html'] = self.generate_html_report()
        reports['markdown'] = self.generate_markdown_report()
        return reports


def create_sample_report():
    """Criar um relatório de exemplo para demonstração"""
    generator = TestReportGenerator()
    
    # Adicionar dados de exemplo
    generator.set_summary(
        total_tests=150,
        passed=142,
        failed=5,
        skipped=3,
        duration=45.67
    )
    
    # Adicionar alguns resultados de teste
    generator.add_test_result("test_login_valid_credentials", "passed", 0.123)
    generator.add_test_result("test_create_user_admin", "passed", 0.456)
    generator.add_test_result("test_invalid_api_endpoint", "failed", 0.789, "AssertionError: Expected 404, got 500")
    generator.add_test_result("test_slow_operation", "skipped", None, "Marked as slow test")
    
    # Adicionar dados de cobertura
    generator.set_coverage_data({
        'percent': 87.5,
        'covered_lines': 1234,
        'total_lines': 1411
    })
    
    # Adicionar métricas de performance
    generator.add_performance_metric("Tempo médio de resposta da API", 125, "ms")
    generator.add_performance_metric("Tempo de carregamento de página", 1.2, "s")
    generator.add_performance_metric("Uso de memória", 256, "MB")
    
    # Adicionar alguns erros
    generator.add_error("Database Connection", "Timeout connecting to database", "Connection timeout after 30 seconds")
    generator.add_error("API Validation", "Invalid JSON format in request", "Expected object, got string")
    
    return generator.generate_all_reports()


if __name__ == "__main__":
    # Criar relatório de exemplo
    reports = create_sample_report()
    print("Relatórios de exemplo gerados:")
    for report_type, filepath in reports.items():
        print(f"- {report_type.upper()}: {filepath}")
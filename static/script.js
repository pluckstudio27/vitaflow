// JavaScript para VitaFlow - Sistema de Almoxarifado

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar tooltips do Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts após 5 segundos
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Validação de formulários
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Formatação de campos de data
    var dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        input.addEventListener('change', function() {
            validateDateRange(this);
        });
    });

    // Formatação de campos numéricos
    var numberInputs = document.querySelectorAll('input[type="number"]');
    numberInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            if (this.value < 0) {
                this.value = 0;
            }
        });
    });

    // Filtros dinâmicos na listagem
    initializeFilters();

    // Confirmação de exclusão
    var deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            var itemName = this.getAttribute('data-item-name');
            if (confirm('Tem certeza que deseja excluir o item "' + itemName + '"?')) {
                window.location.href = this.href;
            }
        });
    });
});

// Função para validar intervalo de datas
function validateDateRange(input) {
    var today = new Date().toISOString().split('T')[0];
    var compraInput = document.getElementById('data_compra');
    var vencimentoInput = document.getElementById('data_vencimento');
    
    if (input.id === 'data_compra') {
        if (input.value > today) {
            showAlert('A data de compra não pode ser futura!', 'warning');
            input.value = today;
        }
        
        if (vencimentoInput && vencimentoInput.value && input.value > vencimentoInput.value) {
            showAlert('A data de compra não pode ser posterior à data de vencimento!', 'warning');
            vencimentoInput.value = '';
        }
    }
    
    if (input.id === 'data_vencimento') {
        if (compraInput && compraInput.value && input.value < compraInput.value) {
            showAlert('A data de vencimento não pode ser anterior à data de compra!', 'warning');
            input.value = '';
        }
    }
}

// Função para mostrar alertas dinâmicos
function showAlert(message, type = 'info') {
    var alertContainer = document.getElementById('alert-container');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'alert-container';
        alertContainer.className = 'position-fixed top-0 end-0 p-3';
        alertContainer.style.zIndex = '1050';
        document.body.appendChild(alertContainer);
    }
    
    var alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alertDiv);
    
    // Auto-remove após 4 segundos
    setTimeout(function() {
        if (alertDiv.parentNode) {
            var bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }
    }, 4000);
}

// Função para inicializar filtros
function initializeFilters() {
    var filterForm = document.getElementById('filter-form');
    if (!filterForm) return;
    
    var inputs = filterForm.querySelectorAll('input, select');
    inputs.forEach(function(input) {
        input.addEventListener('change', function() {
            filterForm.submit();
        });
    });
    
    // Botão de limpar filtros
    var clearButton = document.getElementById('clear-filters');
    if (clearButton) {
        clearButton.addEventListener('click', function() {
            inputs.forEach(function(input) {
                if (input.type === 'text' || input.type === 'date' || input.type === 'number') {
                    input.value = '';
                } else if (input.type === 'select-one') {
                    input.selectedIndex = 0;
                }
            });
            filterForm.submit();
        });
    }
}

// Função para busca em tempo real
function searchTable(inputId, tableId) {
    var input = document.getElementById(inputId);
    var table = document.getElementById(tableId);
    
    if (!input || !table) return;
    
    input.addEventListener('keyup', function() {
        var filter = this.value.toLowerCase();
        var rows = table.getElementsByTagName('tr');
        
        for (var i = 1; i < rows.length; i++) {
            var row = rows[i];
            var cells = row.getElementsByTagName('td');
            var found = false;
            
            for (var j = 0; j < cells.length; j++) {
                var cell = cells[j];
                if (cell.textContent.toLowerCase().indexOf(filter) > -1) {
                    found = true;
                    break;
                }
            }
            
            row.style.display = found ? '' : 'none';
        }
    });
}

// Função para calcular dias até vencimento
function calculateDaysToExpiry(expiryDate) {
    var today = new Date();
    var expiry = new Date(expiryDate);
    var timeDiff = expiry.getTime() - today.getTime();
    var daysDiff = Math.ceil(timeDiff / (1000 * 3600 * 24));
    return daysDiff;
}

// Função para formatar moeda brasileira
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

// Função para formatar data brasileira
function formatDate(dateString) {
    var date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

// Função para exportar dados para CSV
function exportToCSV(tableId, filename) {
    var table = document.getElementById(tableId);
    if (!table) return;
    
    var csv = [];
    var rows = table.querySelectorAll('tr');
    
    for (var i = 0; i < rows.length; i++) {
        var row = [];
        var cols = rows[i].querySelectorAll('td, th');
        
        for (var j = 0; j < cols.length - 1; j++) { // -1 para excluir coluna de ações
            var text = cols[j].textContent.replace(/"/g, '""');
            row.push('"' + text + '"');
        }
        
        csv.push(row.join(','));
    }
    
    var csvContent = csv.join('\n');
    var blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    var link = document.createElement('a');
    
    if (link.download !== undefined) {
        var url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename + '.csv');
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// Função para imprimir relatório
function printReport() {
    window.print();
}

// Função para toggle de modo escuro (futuro)
function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
}

// Carregar preferência de modo escuro
if (localStorage.getItem('darkMode') === 'true') {
    document.body.classList.add('dark-mode');
}

// Função para validar formulário de item
function validateItemForm() {
    var form = document.getElementById('item-form');
    if (!form) return true;
    
    var nome = document.getElementById('nome').value.trim();
    var quantidade = document.getElementById('quantidade').value;
    var dataCompra = document.getElementById('data_compra').value;
    
    if (!nome) {
        showAlert('Nome do item é obrigatório!', 'danger');
        return false;
    }
    
    if (!quantidade || quantidade < 0) {
        showAlert('Quantidade deve ser um número positivo!', 'danger');
        return false;
    }
    
    if (!dataCompra) {
        showAlert('Data de compra é obrigatória!', 'danger');
        return false;
    }
    
    return true;
}

// Função para atualizar contador de caracteres
function updateCharacterCount(textareaId, counterId, maxLength) {
    var textarea = document.getElementById(textareaId);
    var counter = document.getElementById(counterId);
    
    if (!textarea || !counter) return;
    
    textarea.addEventListener('input', function() {
        var remaining = maxLength - this.value.length;
        counter.textContent = remaining + ' caracteres restantes';
        
        if (remaining < 0) {
            counter.classList.add('text-danger');
            counter.classList.remove('text-muted');
        } else {
            counter.classList.remove('text-danger');
            counter.classList.add('text-muted');
        }
    });
}

// Inicializar contador de caracteres para descrição
document.addEventListener('DOMContentLoaded', function() {
    updateCharacterCount('descricao', 'desc-counter', 500);
});
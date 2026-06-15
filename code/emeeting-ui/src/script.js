document.addEventListener('DOMContentLoaded', function() {
    const dateFilter = document.getElementById('date-filter');
    const today = new Date().toISOString().split('T')[0];
    
    if (dateFilter) {
        dateFilter.value = today;
        
        dateFilter.addEventListener('change', function() {
            const selectedDate = this.value;
            const rows = document.querySelectorAll('.sessions-table tbody tr');
            
            rows.forEach(row => {
                const sessionTime = row.cells[0].textContent;
                const sessionDate = sessionTime.split(' ')[0];
                const rowDate = new Date(sessionDate).toISOString().split('T')[0];
                
                if (selectedDate === '' || rowDate === selectedDate) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
});
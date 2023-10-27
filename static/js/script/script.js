$(document).ready(function () {
    function fetchData(page) {
        $.ajax({
            url: `/get_data/${page}`,
            type: 'GET',
            dataType: 'json',
            success: function (response) {
                var data = response.data;
                var tableHtml = '';

                for (var i = 0; i < data.length; i++) {
                    tableHtml += '<tr>';
                    tableHtml += '<td class="td-num">' + data[i]['nama'] + '</td>';
                    tableHtml += '<td class="td-num">' + data[i]['no_kk'] + '</td>';
                    tableHtml += '<td class="td-num">' + data[i]['alamat'] + '</td>';
                    tableHtml += '<td class="td-num">' + data[i]['jumlah_tanggungan'] + '</td>';
                    tableHtml += '<td>' + data[i]['pendidikan'] + '</td>';
                    tableHtml += '<td>' + data[i]['pekerjaan'] + '</td>';
                    tableHtml += '<td class="td-num">' + data[i]['penghasilan'] + '</td>';
                    tableHtml += '<td class="td-num">' + data[i]['jumlah_mobil'] + '</td>';
                    tableHtml += '<td class="td-num">' + data[i]['jumlah_motor'] + '</td>';
                    tableHtml += '<td>' + data[i]['status_kepemilikan'] + '</td>';
                    tableHtml += '<td>' + data[i]['kondisi_rumah'] + '</td>';
                    tableHtml += '<td>' + data[i]['label'] + '</td>';
                    tableHtml += '<td><form action="/delete_data/' + data[i]['id'] + '" method="post"><input type="submit" value="Hapus" class="btn btn-danger"></form></td>';
                    tableHtml += '</tr>';
                }

                $('#data-table tbody').html(tableHtml);
                $('#data-pagination').twbsPagination({
                    totalPages: response.totalPages,
                    visiblePages: 5,
                    onPageClick: function (event, page) {
                        fetchData(page);
                    }
                });
            }
        });
    }

    fetchData(1);

    document.getElementById('logout-form').addEventListener('submit', function (e) {
        var confirmLogout = confirm('Apakah anda yakin ingin keluar dari aplikasi?');
        if (!confirmLogout) {
            e.preventDefault(); 
        }
    });
});

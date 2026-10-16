/* =========================================================================
   宿舍报修管理系统 —— 前端交互脚本
   1. flash 消息以 toast 弹出
   2. 带 js-confirm 的表单提交前弹出二次确认弹窗
   3. 图片上传即时预览 + 前端数量/大小校验
   4. 星级评分联动提示
   ========================================================================= */
(function () {
    'use strict';

    // ---------------------------------------------------- 1. 友好弹窗提示
    document.querySelectorAll('.toast').forEach(function (el) {
        new bootstrap.Toast(el).show();
    });

    // ---------------------------------------------- 2. 危险操作的二次确认
    var confirmEl = document.getElementById('confirmModal');
    if (confirmEl) {
        var confirmModal = new bootstrap.Modal(confirmEl);
        var confirmTitle = document.getElementById('confirmModalTitle');
        var confirmBody = document.getElementById('confirmModalBody');
        var confirmOk = document.getElementById('confirmModalOk');
        var pendingForm = null;

        document.addEventListener('submit', function (event) {
            var form = event.target;
            if (!form.classList || !form.classList.contains('js-confirm')) {
                return;
            }
            if (form.dataset.confirmed === '1') {
                return;
            }
            event.preventDefault();
            pendingForm = form;
            confirmTitle.textContent = form.dataset.confirmTitle || '操作确认';
            confirmBody.textContent = form.dataset.confirm || '确定要执行该操作吗？';
            confirmOk.textContent = form.dataset.confirmOk || '确定';
            confirmOk.className = 'btn ' + (form.dataset.confirmVariant === 'primary' ? 'btn-primary' : 'btn-danger');
            confirmModal.show();
        });

        confirmOk.addEventListener('click', function () {
            if (pendingForm) {
                pendingForm.dataset.confirmed = '1';
                pendingForm.submit();
            }
            confirmModal.hide();
        });
    }

    // ---------------------------------------------------- 3. 图片上传预览
    document.querySelectorAll('input[type="file"][data-preview]').forEach(function (input) {
        var box = document.getElementById(input.dataset.preview);
        var maxFiles = parseInt(input.dataset.max || '3', 10);
        var maxSize = parseInt(input.dataset.maxSize || '5', 10); // MB

        input.addEventListener('change', function () {
            if (!box) {
                return;
            }
            box.innerHTML = '';
            var files = Array.prototype.slice.call(input.files);
            if (files.length > maxFiles) {
                alert('最多只能上传 ' + maxFiles + ' 张图片，多余的图片不会被保存');
                files = files.slice(0, maxFiles);
            }
            files.forEach(function (file) {
                if (file.size > maxSize * 1024 * 1024) {
                    alert('图片「' + file.name + '」超过 ' + maxSize + 'MB，请压缩后再上传');
                    return;
                }
                var reader = new FileReader();
                reader.onload = function (e) {
                    var img = document.createElement('img');
                    img.src = e.target.result;
                    box.appendChild(img);
                };
                reader.readAsDataURL(file);
            });
        });
    });

    // ------------------------------------------------------ 4. 评分文字提示
    var scoreHint = document.getElementById('scoreHint');
    if (scoreHint) {
        var texts = {1: '很不满意', 2: '不太满意', 3: '基本满意', 4: '满意', 5: '非常满意'};
        document.querySelectorAll('.star-rating input').forEach(function (input) {
            input.addEventListener('change', function () {
                scoreHint.textContent = '已选择 ' + input.value + ' 星：' + (texts[input.value] || '');
            });
        });
    }

    // -------------------------------------------------------- 5. 启用工具提示
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
        new bootstrap.Tooltip(el);
    });
})();

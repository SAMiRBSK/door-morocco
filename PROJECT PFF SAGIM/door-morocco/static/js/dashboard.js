/**
 * Door Morocco — Dashboard Interactions
 * Image preview, dynamic affiliate links, form toggle.
 */
document.addEventListener('DOMContentLoaded', () => {

  /* ── Toggle Add-Service form ─────────────────────────── */
  const toggleBtn = document.getElementById('toggleBtn');
  const form = document.getElementById('addServiceForm');
  if (toggleBtn && form) {
    const icon = toggleBtn.querySelector('.dash-section__toggle-icon');
    let open = true;

    document.getElementById('toggleAddForm').addEventListener('click', (e) => {
      if (e.target.closest('.dash-section__toggle') || e.target.closest('.dash-section__title')) {
        open = !open;
        form.style.display = open ? '' : 'none';
        icon.style.transform = open ? 'rotate(0)' : 'rotate(-90deg)';
      }
    });
  }

  /* ── Image upload preview ────────────────────────────── */
  const fileInput = document.getElementById('serviceImage');
  const uploadZone = document.getElementById('uploadZone');
  const placeholder = document.getElementById('uploadPlaceholder');
  const previewWrap = document.getElementById('uploadPreview');
  const previewImg = document.getElementById('previewImg');
  const removeBtn = document.getElementById('removeImage');

  if (fileInput && uploadZone) {
    // Drag & drop
    uploadZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      uploadZone.classList.add('dash-upload--dragover');
    });
    uploadZone.addEventListener('dragleave', () => {
      uploadZone.classList.remove('dash-upload--dragover');
    });
    uploadZone.addEventListener('drop', (e) => {
      e.preventDefault();
      uploadZone.classList.remove('dash-upload--dragover');
      if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        showPreview(e.dataTransfer.files[0]);
      }
    });

    // Click to select
    fileInput.addEventListener('change', () => {
      if (fileInput.files.length) showPreview(fileInput.files[0]);
    });

    // Remove image
    if (removeBtn) {
      removeBtn.addEventListener('click', () => {
        fileInput.value = '';
        placeholder.style.display = '';
        previewWrap.style.display = 'none';
      });
    }

    function showPreview(file) {
      // Validate size client-side (5 MB)
      if (file.size > 5 * 1024 * 1024) {
        alert('Image must be smaller than 5 MB.');
        fileInput.value = '';
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        previewImg.src = e.target.result;
        placeholder.style.display = 'none';
        previewWrap.style.display = 'flex';
      };
      reader.readAsDataURL(file);
    }
  }

  /* ── Dynamic affiliate links ─────────────────────────── */
  const linksContainer = document.getElementById('affiliateLinks');
  const addLinkBtn = document.getElementById('addLinkBtn');
  let rowCount = 1;

  if (addLinkBtn && linksContainer) {
    addLinkBtn.addEventListener('click', () => {
      const row = document.createElement('div');
      row.className = 'affiliate-link';
      row.id = 'affiliateRow-' + rowCount;
      row.innerHTML =
        '<input class="dash-form__input dash-form__input--sm" type="text" name="link_site_name[]" placeholder="Site (e.g. Booking.com)">' +
        '<input class="dash-form__input dash-form__input--sm" type="number" name="link_price[]" placeholder="Price (MAD)" step="0.01" min="0">' +
        '<input class="dash-form__input dash-form__input--sm" type="url" name="link_url[]" placeholder="https://...">' +
        '<button type="button" class="affiliate-link__remove" onclick="removeAffiliateRow(this)" aria-label="Remove">&times;</button>';

      // Animate in
      row.style.opacity = '0';
      row.style.transform = 'translateY(10px)';
      linksContainer.appendChild(row);
      requestAnimationFrame(() => {
        row.style.transition = 'opacity 0.3s, transform 0.3s';
        row.style.opacity = '1';
        row.style.transform = 'translateY(0)';
      });

      rowCount++;
    });
  }
});

/* ── Remove affiliate link row (global) ────────────────── */
function removeAffiliateRow(btn) {
  const row = btn.closest('.affiliate-link');
  row.style.opacity = '0';
  row.style.transform = 'translateX(20px)';
  setTimeout(() => row.remove(), 300);
}

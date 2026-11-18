css_content = """

/* ═══════════════════════════════════════════════════════════════════════════
   MOCKUP 4 : GESTION DES LOTS & PÉREMPTION (ShelfLifePro Style)
   ═══════════════════════════════════════════════════════════════════════════ */
.pg-batch-stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 22px;
}

@media (max-width: 992px) {
  .pg-batch-stat-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 576px) {
  .pg-batch-stat-row {
    grid-template-columns: 1fr;
  }
}

.pg-batch-card {
  background: #ffffff;
  border: 1px solid var(--pg-line, #e2e8f0);
  border-radius: 12px;
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
  text-decoration: none !important;
  color: inherit !important;
  cursor: pointer;
}

.pg-batch-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
  border-color: #cbd5e1;
}

.pg-batch-card-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.45rem;
  flex-shrink: 0;
}

.pg-batch-card-total {
  border-left: 4px solid #3b82f6;
}
.pg-batch-card-total .pg-batch-card-icon {
  background: #eff6ff;
  color: #2563eb;
}

.pg-batch-card-perime {
  border-left: 4px solid #ef4444;
}
.pg-batch-card-perime .pg-batch-card-icon {
  background: #fef2f2;
  color: #dc2626;
}

.pg-batch-card-proche {
  border-left: 4px solid #f59e0b;
}
.pg-batch-card-proche .pg-batch-card-icon {
  background: #fffbeb;
  color: #d97706;
}

.pg-batch-card-valide {
  border-left: 4px solid #10b981;
}
.pg-batch-card-valide .pg-batch-card-icon {
  background: #ecfdf5;
  color: #059669;
}

.pg-batch-card-label {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
  margin-bottom: 2px;
}

.pg-batch-card-num {
  font-size: 1.85rem;
  font-weight: 800;
  line-height: 1.1;
  color: #0f172a;
}

.pg-table-thumb {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  object-fit: cover;
  border: 1px solid #e2e8f0;
  background-color: #f8fafc;
  flex-shrink: 0;
}

.pg-table-thumb-placeholder {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  border: 1px solid #cbd5e1;
  flex-shrink: 0;
}

.badge-overdue {
  background-color: #fee2e2;
  color: #b91c1c;
  border: 1px solid #fca5a5;
  font-weight: 700;
  font-size: 0.74rem;
  padding: 4px 8px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.badge-expiring-soon {
  background-color: #fef3c7;
  color: #b45309;
  border: 1px solid #fcd34d;
  font-weight: 700;
  font-size: 0.74rem;
  padding: 4px 8px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.badge-valid {
  background-color: #d1fae5;
  color: #065f46;
  border: 1px solid #6ee7b7;
  font-weight: 700;
  font-size: 0.74rem;
  padding: 4px 8px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* ═══════════════════════════════════════════════════════════════════════════
   MOCKUP 1 : TABLEAU DE BORD (Hero Banner & Smart Insights)
   ═══════════════════════════════════════════════════════════════════════════ */
.pg-hero-banner {
  background: linear-gradient(135deg, #064e3b 0%, #047857 50%, #059669 100%);
  color: #ffffff;
  border-radius: 16px;
  padding: 28px 32px;
  margin-bottom: 24px;
  box-shadow: 0 10px 25px -5px rgba(5, 150, 105, 0.25);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  position: relative;
  overflow: hidden;
}

.pg-hero-banner::after {
  content: "";
  position: absolute;
  right: -40px;
  top: -40px;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.12) 0%, rgba(255, 255, 255, 0) 70%);
  pointer-events: none;
}

.pg-hero-banner-content h1,
.pg-hero-banner-title {
  font-size: 1.65rem;
  font-weight: 800;
  color: #ffffff;
  margin-bottom: 6px;
  letter-spacing: -0.02em;
}

.pg-hero-banner-sub {
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.92rem;
  margin: 0;
}

.pg-insights-widget {
  background: #0f172a;
  color: #f8fafc;
  border-radius: 14px;
  padding: 22px;
  border: 1px solid #1e293b;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
}

.pg-insights-title {
  color: #38bdf8;
  font-size: 0.95rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.pg-insights-item {
  padding: 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  margin-bottom: 12px;
}
.pg-insights-item:last-child {
  margin-bottom: 0;
}

/* ═══════════════════════════════════════════════════════════════════════════
   MOCKUP 3 : CAISSE ENREGISTREUSE & POS (Odoo POS Style)
   ═══════════════════════════════════════════════════════════════════════════ */
.pg-pos-cats {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 8px;
  margin-bottom: 16px;
  scrollbar-width: thin;
}

.pg-pos-cat-btn {
  white-space: nowrap;
  padding: 8px 16px;
  border-radius: 24px;
  font-size: 0.84rem;
  font-weight: 600;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  color: #334155;
  transition: all 0.18s ease;
  cursor: pointer;
}

.pg-pos-cat-btn:hover,
.pg-pos-cat-btn.active {
  background: #059669;
  color: #ffffff;
  border-color: #059669;
  box-shadow: 0 2px 6px rgba(5, 150, 105, 0.25);
}

.pg-product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 14px;
  max-height: 560px;
  overflow-y: auto;
  padding-right: 4px;
}

.pg-pos-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
  cursor: pointer;
  user-select: none;
  text-align: left;
}

.pg-pos-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.08);
  border-color: #059669;
}

.pg-pos-card-img-wrap {
  width: 100%;
  height: 100px;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-bottom: 1px solid #f1f5f9;
}

.pg-pos-card-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.pg-pos-card-body {
  padding: 10px 12px;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.pg-pos-card-name {
  font-size: 0.85rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pg-pos-card-price {
  font-size: 0.95rem;
  font-weight: 800;
  color: #059669;
}

.pg-pos-card-stock {
  font-size: 0.7rem;
  font-weight: 600;
  color: #64748b;
}

/* Numpad */
.pg-numpad {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  margin-top: 12px;
}

.pg-numpad-btn {
  height: 44px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  font-size: 1.1rem;
  font-weight: 700;
  color: #1e293b;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.12s ease;
}

.pg-numpad-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.pg-numpad-btn:active {
  transform: scale(0.96);
}
"""

with open('static/css/pharmagest.css', 'a', encoding='utf-8') as f:
    f.write(css_content)

print("Appended successfully.")


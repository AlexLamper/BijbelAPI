function showEl(id, show) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle('hidden', !show);
}

function stripeErrorMessage(data, res) {
    if (data && typeof data.message === 'string') return data.message;
    if (data && typeof data.detail === 'string') return data.detail;
    if (data && data.detail) return JSON.stringify(data.detail);
    return `Er ging iets mis (${res.status}).`;
}

function setButtonLoading(btn, loading, labelBusy) {
    if (!btn) return;
    if (loading) {
        if (!btn.dataset.labelIdle) btn.dataset.labelIdle = btn.textContent.trim();
        btn.disabled = true;
        btn.textContent = labelBusy;
        btn.setAttribute('aria-busy', 'true');
    } else {
        btn.disabled = false;
        if (btn.dataset.labelIdle) btn.textContent = btn.dataset.labelIdle;
        btn.removeAttribute('aria-busy');
    }
}

async function startStripeCheckout(plan) {
    const errEl = document.getElementById('checkoutError');
    if (errEl) {
        errEl.textContent = '';
        errEl.classList.add('hidden');
    }
    const emailInput = document.getElementById('checkoutEmail');
    const email = emailInput ? emailInput.value.trim() : '';
    if (!email || !email.includes('@')) {
        if (errEl) {
            errEl.textContent = 'Vul een geldig e-mailadres in voor Checkout.';
            errEl.classList.remove('hidden');
        }
        return;
    }
    const btn =
        plan === 'pro_yearly'
            ? document.getElementById('btnCheckoutYearly')
            : document.getElementById('btnCheckoutMonthly');
    setButtonLoading(btn, true, 'Bezig…');
    try {
        const res = await fetch('/billing/checkout-session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify({ email, plan }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            if (errEl) {
                errEl.textContent = stripeErrorMessage(data, res);
                errEl.classList.remove('hidden');
            }
            return;
        }
        if (data.checkout_url) {
            window.location.href = data.checkout_url;
            return;
        }
        if (errEl) {
            errEl.textContent = 'Geen checkout-URL ontvangen. Controleer de Stripe-configuratie.';
            errEl.classList.remove('hidden');
        }
    } catch {
        if (errEl) {
            errEl.textContent =
                'Netwerkfout of geen verbinding met de server. Controleer of je op de live site zit (niet file://) en of de API bereikbaar is.';
            errEl.classList.remove('hidden');
        }
    } finally {
        setButtonLoading(document.getElementById('btnCheckoutMonthly'), false);
        setButtonLoading(document.getElementById('btnCheckoutYearly'), false);
    }
}

async function openStripePortal() {
    const errEl = document.getElementById('portalError');
    if (errEl) {
        errEl.textContent = '';
        errEl.classList.add('hidden');
    }
    const emailInput = document.getElementById('portalEmail');
    const email = emailInput ? emailInput.value.trim() : '';
    if (!email || !email.includes('@')) {
        if (errEl) {
            errEl.textContent = 'Vul het e-mailadres in waarmee je Pro hebt afgenomen.';
            errEl.classList.remove('hidden');
        }
        return;
    }
    const btn = document.getElementById('btnPortal');
    setButtonLoading(btn, true, 'Bezig…');
    try {
        const res = await fetch('/billing/portal-session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify({ email }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            if (errEl) {
                errEl.textContent = stripeErrorMessage(data, res);
                errEl.classList.remove('hidden');
            }
            return;
        }
        if (data.portal_url) {
            window.location.href = data.portal_url;
            return;
        }
        if (errEl) {
            errEl.textContent = 'Geen portaal-URL ontvangen.';
            errEl.classList.remove('hidden');
        }
    } catch {
        if (errEl) {
            errEl.textContent = 'Netwerkfout. Probeer het later opnieuw.';
            errEl.classList.remove('hidden');
        }
    } finally {
        setButtonLoading(btn, false);
    }
}

function initBillingAndBanners() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('checkout') === 'success') showEl('checkoutBanner', true);
    if (params.get('checkout') === 'cancelled') showEl('checkoutCancelledBanner', true);

    document.getElementById('btnCheckoutMonthly')?.addEventListener('click', () => startStripeCheckout('pro_monthly'));
    document.getElementById('btnCheckoutYearly')?.addEventListener('click', () => startStripeCheckout('pro_yearly'));
    document.getElementById('btnPortal')?.addEventListener('click', openStripePortal);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBillingAndBanners);
} else {
    initBillingAndBanners();
}

// Zoek een specifiek vers
const verseForm = document.getElementById('verseForm');
const verseResult = document.getElementById('verseResult');
verseForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!verseResult) return;
    verseResult.textContent = 'Bezig met zoeken...';
    const book = document.getElementById('book')?.value;
    const chapter = document.getElementById('chapter')?.value;
    const verse = document.getElementById('verse')?.value;
    try {
        const res = await fetch(`/api/verse?book=${encodeURIComponent(book)}&chapter=${chapter}&verse=${verse}`);
        if (!res.ok) throw new Error('Niet gevonden of fout in API');
        const data = await res.json();
        verseResult.innerHTML = `<b>${data.book} ${data.chapter}:${data.verse}</b><br>${data.text}`;
    } catch (err) {
        verseResult.textContent = 'Kon vers niet ophalen. Controleer je invoer.';
    }
});

// Dagtekst ophalen
const daytextBtn = document.getElementById('getDaytext');
const daytextResult = document.getElementById('daytextResult');
daytextBtn?.addEventListener('click', async () => {
    if (!daytextResult) return;
    daytextResult.textContent = 'Bezig met ophalen...';
    try {
        const res = await fetch('/api/daytext');
        if (!res.ok) throw new Error('Fout in API');
        const data = await res.json();
        daytextResult.innerHTML = `<b>${data.book} ${data.chapter}:${data.verse}</b><br>${data.text}`;
    } catch (err) {
        console.error('Kon dagtekst niet ophalen:', err);
        daytextResult.textContent = 'Kon dagtekst niet ophalen. ' + (err.message || err);
    }
});

// Laad boekenlijst in dropdown
async function loadBooksDropdown() {
    const select = document.getElementById('bookChapterSelect');
    if (!select) return;
    select.innerHTML = '<option value="">Laden...</option>';
    try {
        const res = await fetch('/api/books');
        const books = await res.json();
        if (!Array.isArray(books)) {
            select.innerHTML = '<option>Ongeldig antwoord</option>';
            return;
        }
        select.innerHTML = books.map((book) => `<option value="${book}">${book}</option>`).join('');
    } catch {
        select.innerHTML = '<option>Fout bij laden</option>';
    }
}
loadBooksDropdown();

// Hoofdstuk ophalen
const chapterForm = document.getElementById('chapterForm');
const chapterResult = document.getElementById('chapterResult');
chapterForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!chapterResult) return;
    chapterResult.textContent = 'Bezig met laden...';
    const bookSelect = document.getElementById('bookChapterSelect');
    const chapterNum = document.getElementById('chapterNum');
    const book = bookSelect?.value;
    const chapter = chapterNum?.value;
    try {
        const res = await fetch(`/api/chapter?book=${encodeURIComponent(book)}&chapter=${chapter}`);
        if (!res.ok) throw new Error('Niet gevonden of fout in API');
        const data = await res.json();
        let html = `<b>${data.book} ${data.chapter}</b><br><div class="card">`;
        for (const [vers, tekst] of Object.entries(data.verses)) {
            html += `<b>${vers}</b> ${tekst}<br>`;
        }
        html += '</div>';
        chapterResult.innerHTML = html;
    } catch (err) {
        chapterResult.textContent = 'Kon hoofdstuk niet ophalen. Controleer je invoer.';
    }
});

// Kopieerknoppen
function setupCopyButtons() {
    const btns = document.querySelectorAll('.copy-btn');
    btns.forEach((btn) => {
        btn.addEventListener('click', () => {
            const url = btn.getAttribute('data-url');
            navigator.clipboard.writeText(url);
            btn.textContent = 'Gekopieerd!';
            btn.classList.add('copied');
            setTimeout(() => {
                btn.textContent = 'Kopieer';
                btn.classList.remove('copied');
            }, 1200);
        });
    });
}
setupCopyButtons();

// API test buttons
function setupApiTestButtons() {
    const btns = document.querySelectorAll('.api-test-btn');
    btns.forEach((btn) => {
        btn.addEventListener('click', async () => {
            const url = btn.getAttribute('data-url');
            const resultDiv = btn.parentElement?.querySelector('.api-test-result');
            if (!resultDiv) return;
            resultDiv.textContent = 'Bezig...';
            try {
                const res = await fetch(url);
                const data = await res.json();
                resultDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            } catch (err) {
                resultDiv.textContent = 'Fout bij ophalen of geen geldige JSON.';
            }
        });
    });
}
setupApiTestButtons();

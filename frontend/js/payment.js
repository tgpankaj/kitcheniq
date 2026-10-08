/* KitchenIQ — Razorpay Payment Checkout */

const RAZORPAY_SCRIPT = 'https://checkout.razorpay.com/v1/checkout.js';


// ============================================================
// LOAD RAZORPAY SCRIPT
// ============================================================

function loadRazorpayScript() {
    return new Promise((resolve, reject) => {
        if (window.Razorpay) return resolve(true);

        const script = document.createElement('script');
        script.src = RAZORPAY_SCRIPT;
        script.onload = () => resolve(true);
        script.onerror = () => reject(new Error('Failed to load Razorpay'));
        document.head.appendChild(script);
    });
}


// ============================================================
// MAIN CHECKOUT FLOW
// ============================================================

async function initiatePayment(planId, planName, amount) {
    const token = localStorage.getItem('token');
    const API = window.API_URL;

    if (!token) {
        window.location.href = 'login.html';
        return;
    }

    try {
        // 1. Create order on backend
        const res = await fetch(API + '/api/payments/create-order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token,
            },
            body: JSON.stringify({ plan: planId }),
        });

        const order = await res.json();
        if (!res.ok) throw new Error(order.error);

        // 2. Mock mode — simulate success directly
        if (order.is_mock) {
            return await simulateMockPayment(planId, planName, order);
        }

        // 3. Real Razorpay checkout
        await loadRazorpayScript();

        const user = JSON.parse(localStorage.getItem('user') || '{}');

        const options = {
            key: order.key_id,
            amount: order.amount * 100,
            currency: order.currency,
            name: 'KitchenIQ',
            description: `${planName} Plan — Monthly Subscription`,
            image: '/assets/logo.png',
            order_id: order.order_id,
            prefill: {
                name: user.full_name || '',
                email: user.email || '',
            },
            theme: { color: '#2563eb' },
            handler: async function(response) {
                await verifyPayment(response, planName);
            },
            modal: {
                ondismiss: function() {
                    if (window.showToast) window.showToast('Payment cancelled', 'info');
                },
            },
        };

        const rzp = new Razorpay(options);
        rzp.open();

    } catch (e) {
        if (window.showToast) window.showToast(e.message, 'danger');
        else alert(e.message);
    }
}


// ============================================================
// MOCK MODE — Simulate Successful Payment
// ============================================================

async function simulateMockPayment(planId, planName, order) {
    const API = window.API_URL;
    const token = localStorage.getItem('token');

    // Show a mock dialog
    const confirmed = confirm(
        `💳 MOCK PAYMENT\n\n` +
        `Plan: ${planName}\n` +
        `Amount: ₹${order.amount}\n` +
        `Order: ${order.order_id}\n\n` +
        `Click OK to simulate successful payment.`
    );

    if (!confirmed) {
        if (window.showToast) window.showToast('Payment cancelled', 'info');
        return;
    }

    // Verify with mock signature
    const verifyRes = await fetch(API + '/api/payments/verify', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token,
        },
        body: JSON.stringify({
            razorpay_order_id: order.order_id,
            razorpay_payment_id: 'pay_mock_' + Date.now(),
            razorpay_signature: 'mock_signature',
        }),
    });

    const result = await verifyRes.json();
    if (!verifyRes.ok) {
        if (window.showToast) window.showToast(result.error, 'danger');
        return;
    }

    if (window.showToast) window.showToast(`🎉 ${planName} plan activated!`, 'success');
    setTimeout(() => window.location.reload(), 1500);
}


// ============================================================
// REAL MODE — Verify After Razorpay Success
// ============================================================

async function verifyPayment(response, planName) {
    const API = window.API_URL;
    const token = localStorage.getItem('token');

    try {
        const res = await fetch(API + '/api/payments/verify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token,
            },
            body: JSON.stringify({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
            }),
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        if (window.showToast) window.showToast(`🎉 ${planName} plan activated!`, 'success');
        setTimeout(() => window.location.reload(), 1500);
    } catch (e) {
        if (window.showToast) window.showToast('Payment verification failed: ' + e.message, 'danger');
    }
}


// ============================================================
// EXPORT
// ============================================================

window.initiatePayment = initiatePayment;

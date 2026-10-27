// ====================================================================
// PROJECT KASHI - Client-side Utilities
// Handles Modal Dialogs, Operations Tabs, and Interactive Helpers
// ====================================================================

document.addEventListener("DOMContentLoaded", () => {
    // 1. Modal Dialog Logic
    const openModalBtns = document.querySelectorAll("[data-modal-target]");
    const closeModalBtns = document.querySelectorAll("[data-modal-close]");

    openModalBtns.forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            const modalId = btn.getAttribute("data-modal-target");
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.add("open");
            }
        });
    });

    closeModalBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const modal = btn.closest(".modal");
            if (modal) {
                modal.classList.remove("open");
            }
        });
    });

    window.addEventListener("click", (e) => {
        if (e.target.classList.contains("modal")) {
            e.target.classList.remove("open");
        }
    });

    // 2. Tab switching logic for Operations (Deposit, Withdraw, Transfer)
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-tab-target");
            
            tabBtns.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.style.display = "none");

            btn.classList.add("active");
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.style.display = "block";
            }
        });
    });

    // 3. Auto-dismiss alerts after 6 seconds
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.5s ease, transform 0.5s ease";
            alert.style.opacity = "0";
            alert.style.transform = "translateY(-10px)";
            setTimeout(() => alert.remove(), 500);
        }, 6000);
    });

    // 4. Live EMI Calculator widget if present
    const loanAmountInput = document.getElementById("calc-loan-amount");
    const interestRateInput = document.getElementById("calc-interest-rate");
    const tenureMonthsInput = document.getElementById("calc-tenure-months");
    const emiResultDisplay = document.getElementById("calc-emi-result");

    function calculateLiveEMI() {
        if (!loanAmountInput || !interestRateInput || !tenureMonthsInput || !emiResultDisplay) return;
        const P = parseFloat(loanAmountInput.value) || 0;
        const annualR = parseFloat(interestRateInput.value) || 0;
        const N = parseInt(tenureMonthsInput.value) || 0;

        if (P <= 0 || annualR <= 0 || N <= 0) {
            emiResultDisplay.textContent = "₹0.00 / mo";
            return;
        }

        const r = (annualR / 12) / 100;
        const emi = (P * r * Math.pow(1 + r, N)) / (Math.pow(1 + r, N) - 1);
        emiResultDisplay.textContent = `₹${emi.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} / mo`;
    }

    if (loanAmountInput && interestRateInput && tenureMonthsInput) {
        loanAmountInput.addEventListener("input", calculateLiveEMI);
        interestRateInput.addEventListener("input", calculateLiveEMI);
        tenureMonthsInput.addEventListener("input", calculateLiveEMI);
    }
});

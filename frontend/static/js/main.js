// ====================================================================
// SHREEHARI FINANCE - Interactive Client Enhancements
// ====================================================================

document.addEventListener("DOMContentLoaded", () => {
    // 1. Quick Amount Chips handler
    const chips = document.querySelectorAll(".amount-chip");
    const amountInput = document.getElementById("amount-input");

    chips.forEach(chip => {
        chip.addEventListener("click", () => {
            if (amountInput) {
                const val = chip.getAttribute("data-val");
                amountInput.value = val;
                amountInput.focus();
                amountInput.dispatchEvent(new Event('input'));
            }
        });
    });

    // 2. Radio Card selection visual state
    const radioCards = document.querySelectorAll(".radio-card");
    radioCards.forEach(card => {
        card.addEventListener("click", () => {
            radioCards.forEach(c => c.classList.remove("active"));
            card.classList.add("active");
            const radio = card.querySelector("input[type='radio']");
            if (radio) {
                radio.checked = true;
            }
        });
    });

    // 3. Deposit Dynamic Balance Projection
    const depositSelect = document.getElementById("deposit-account-select");
    const depositCurrentBal = document.getElementById("deposit-current-bal");
    const depositProjectedBal = document.getElementById("deposit-projected-bal");

    function updateDepositPreview() {
        if (!depositSelect || !depositCurrentBal) return;
        const opt = depositSelect.options[depositSelect.selectedIndex];
        const currentBal = opt && opt.getAttribute("data-balance") ? parseFloat(opt.getAttribute("data-balance")) : 0;
        const amt = amountInput && amountInput.value ? parseFloat(amountInput.value) : 0;

        depositCurrentBal.textContent = `₹${currentBal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        if (depositProjectedBal) {
            const projected = currentBal + (isNaN(amt) ? 0 : amt);
            depositProjectedBal.textContent = `₹${projected.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        }
    }

    if (depositSelect) {
        depositSelect.addEventListener("change", updateDepositPreview);
        if (amountInput) amountInput.addEventListener("input", updateDepositPreview);
        updateDepositPreview();
    }

    // 4. Withdraw Dynamic Balance & Overdraft Warning
    const withdrawSelect = document.getElementById("withdraw-account-select");
    const withdrawCurrentBal = document.getElementById("withdraw-current-bal");
    const withdrawProjectedBal = document.getElementById("withdraw-projected-bal");
    const withdrawWarning = document.getElementById("withdraw-warning-box");
    const withdrawSubmitBtn = document.getElementById("withdraw-submit-btn");

    function updateWithdrawPreview() {
        if (!withdrawSelect || !withdrawCurrentBal) return;
        const opt = withdrawSelect.options[withdrawSelect.selectedIndex];
        const currentBal = opt && opt.getAttribute("data-balance") ? parseFloat(opt.getAttribute("data-balance")) : 0;
        const amt = amountInput && amountInput.value ? parseFloat(amountInput.value) : 0;

        withdrawCurrentBal.textContent = `₹${currentBal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

        if (withdrawProjectedBal) {
            const remaining = currentBal - (isNaN(amt) ? 0 : amt);
            withdrawProjectedBal.textContent = `₹${remaining.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

            if (amt > currentBal && amt > 0) {
                withdrawProjectedBal.style.color = "#dc2626";
                if (withdrawWarning) withdrawWarning.style.display = "block";
            } else {
                withdrawProjectedBal.style.color = "#047857";
                if (withdrawWarning) withdrawWarning.style.display = "none";
            }
        }
    }

    if (withdrawSelect) {
        withdrawSelect.addEventListener("change", updateWithdrawPreview);
        if (amountInput) amountInput.addEventListener("input", updateWithdrawPreview);
        updateWithdrawPreview();
    }

    // 5. Transfer Sender Balance Preview
    const senderSelect = document.getElementById("sender-account-select");
    const balancePreview = document.getElementById("available-balance-display");

    function updateSenderBalancePreview() {
        if (!senderSelect || !balancePreview) return;
        const opt = senderSelect.options[senderSelect.selectedIndex];
        const bal = opt ? opt.getAttribute("data-balance") : null;
        if (bal !== null && bal !== undefined) {
            const formatted = parseFloat(bal).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            balancePreview.textContent = `₹${formatted}`;
        } else {
            balancePreview.textContent = "₹0.00";
        }
    }

    if (senderSelect) {
        senderSelect.addEventListener("change", updateSenderBalancePreview);
        updateSenderBalancePreview();
    }

    // 6. Live Loan EMI Calculator
    const loanAmtInput = document.getElementById("loan-amount-input");
    const loanRateInput = document.getElementById("loan-rate-input");
    const loanTenureInput = document.getElementById("loan-tenure-input");
    const emiDisplay = document.getElementById("calculated-emi-display");

    function calculateEMI() {
        if (!loanAmtInput || !loanRateInput || !loanTenureInput || !emiDisplay) return;
        const P = parseFloat(loanAmtInput.value);
        const annualRate = parseFloat(loanRateInput.value);
        const N = parseInt(loanTenureInput.value);

        if (isNaN(P) || isNaN(annualRate) || isNaN(N) || P <= 0 || N <= 0) {
            emiDisplay.textContent = "₹0.00 / mo";
            return;
        }

        const R = (annualRate / 12) / 100;
        // EMI formula: [P * R * (1+R)^N] / [(1+R)^N - 1]
        const emi = (P * R * Math.pow(1 + R, N)) / (Math.pow(1 + R, N) - 1);
        if (!isNaN(emi) && isFinite(emi)) {
            emiDisplay.textContent = `₹${Math.round(emi).toLocaleString('en-IN')} / mo`;
        }
    }

    if (loanAmtInput && loanRateInput && loanTenureInput) {
        loanAmtInput.addEventListener("input", calculateEMI);
        loanRateInput.addEventListener("input", calculateEMI);
        loanTenureInput.addEventListener("input", calculateEMI);
        calculateEMI();
    }

    // 7. Auto dismiss alert banners
    const alerts = document.querySelectorAll(".alert-banner");
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.4s ease, transform 0.4s ease";
            alert.style.opacity = "0";
            alert.style.transform = "translateY(-6px)";
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });

    // 8. Instant Client Table Filter (for fast search)
    const clientFilterInput = document.getElementById("table-live-search");
    if (clientFilterInput) {
        clientFilterInput.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase().trim();
            const rows = document.querySelectorAll("tbody tr");
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(query)) {
                    row.style.display = "";
                } else {
                    row.style.display = "none";
                }
            });
        });
    }
});

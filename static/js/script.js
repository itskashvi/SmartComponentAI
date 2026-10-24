/**
 * static/js/script.js
 * Interactive frontend logic for SmartComponentAI:
 * - One-click project preset auto-filling
 * - Dynamic asynchronous hardware setup compatibility testing
 */

// Global state of currently active components in the results setup
let activeSetupComponents = [];

document.addEventListener("DOMContentLoaded", () => {
    // Initialize active components from existing toggle buttons
    const activeButtons = document.querySelectorAll(".btn-toggle-setup.active");
    activeSetupComponents = Array.from(activeButtons).map(btn => btn.dataset.id);

    // Form submit loading state
    const form = document.getElementById("recommendation-form");
    if (form) {
        form.addEventListener("submit", () => {
            const btn = document.getElementById("submit-btn");
            if (btn) {
                btn.innerHTML = `<span class="btn-text">Analyzing Requirements & Checking Pins...</span>`;
                btn.style.opacity = "0.85";
                btn.style.pointerEvents = "none";
            }
        });
    }
});

/**
 * Auto-populates the project requirement form with preset templates.
 */
function fillPreset(description, platform, budget, existingParts) {
    const descInput = document.getElementById("project_description");
    const platSelect = document.getElementById("platform");
    const budgetInput = document.getElementById("budget");
    const partsInput = document.getElementById("existing_parts");

    if (descInput) descInput.value = description;
    if (budgetInput) budgetInput.value = budget;
    if (partsInput) partsInput.value = existingParts;

    if (platSelect) {
        // Match by option value (component_id)
        for (let i = 0; i < platSelect.options.length; i++) {
            if (platSelect.options[i].value === platform) {
                platSelect.selectedIndex = i;
                break;
            }
        }
    }

    // Smooth scroll to form
    const formCard = document.querySelector(".form-container-card");
    if (formCard) {
        formCard.scrollIntoView({ behavior: "smooth" });
        formCard.style.outline = "2px solid #6db1bf";
        setTimeout(() => {
            formCard.style.outline = "none";
        }, 1200);
    }
}

/**
 * Toggles a component into or out of the active hardware setup
 * and calls the /check-compatibility API to update the live diagnostics.
 */
async function toggleSetupComponent(componentId, buttonElem) {
    const isCurrentlyActive = activeSetupComponents.includes(componentId);

    if (isCurrentlyActive) {
        activeSetupComponents = activeSetupComponents.filter(id => id !== componentId);
        buttonElem.classList.remove("active");
        buttonElem.textContent = "+ Add to Setup";
    } else {
        activeSetupComponents.push(componentId);
        buttonElem.classList.add("active");
        buttonElem.textContent = "In Setup";
    }

    const platformElem = document.getElementById("active-platform");
    const platformId = platformElem ? (platformElem.dataset.platformId || "esp32") : "esp32";

    // Show quick subtle loading animation on overall status box
    const statusBox = document.getElementById("overall-status-box");
    if (statusBox) {
        statusBox.style.opacity = "0.6";
    }

    try {
        const response = await fetch("/check-compatibility", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                platform_id: platformId,
                component_ids: activeSetupComponents
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const report = await response.json();
        updateCompatibilityUI(report);
    } catch (err) {
        console.error("Error updating compatibility setup:", err);
    } finally {
        if (statusBox) {
            statusBox.style.opacity = "1";
        }
    }
}

/**
 * Updates the compatibility diagnostics DOM based on the API response.
 */
function updateCompatibilityUI(report) {
    // 1. Overall Status Box
    const statusBox = document.getElementById("overall-status-box");
    const statusText = document.getElementById("overall-status-text");
    const statusDesc = document.getElementById("overall-status-desc");

    if (statusBox && statusText && statusDesc) {
        statusBox.className = `compatibility-hero-status status-${report.overall_status}`;
        const iconElem = statusBox.querySelector(".status-indicator-badge");

        if (report.overall_status === "compatible") {
            if (iconElem) iconElem.textContent = "OK";
            statusText.textContent = "COMPATIBLE SETUP";
            statusDesc.textContent = "All components operate within safe voltage limits, supported communication protocols, and pin budgets.";
        } else if (report.overall_status === "warning") {
            if (iconElem) iconElem.textContent = "WARN";
            statusText.textContent = "COMPATIBILITY WARNING";
            statusDesc.textContent = "Setup requires level shifting, redundant sensor pruning, or external power, but is achievable.";
        } else {
            if (iconElem) iconElem.textContent = "ERR";
            statusText.textContent = "INCOMPATIBLE HARDWARE SETUP";
            statusDesc.textContent = "Fatal interface or electrical mismatch detected. Review detailed diagnostics below.";
        }
    }

    // 2. Resource Gauges: Pin budget
    const pinGaugeVal = document.getElementById("pin-gauge-val");
    const pinBar = document.getElementById("pin-progress-bar");
    if (pinGaugeVal && report.pin_budget) {
        pinGaugeVal.textContent = `${report.pin_budget.used} / ${report.pin_budget.available} Pins (${report.pin_budget.percentage}%)`;
    }
    if (pinBar && report.pin_budget) {
        pinBar.style.width = `${report.pin_budget.percentage}%`;
        pinBar.className = "progress-bar-fill";
        if (report.pin_budget.percentage > 85) {
            pinBar.classList.add("progress-danger");
        } else if (report.pin_budget.percentage > 65) {
            pinBar.classList.add("progress-warn");
        }
    }

    // 3. Resource Gauges: Power budget
    const powerGaugeVal = document.getElementById("power-gauge-val");
    const powerGaugeNote = document.getElementById("power-gauge-note");
    if (powerGaugeVal && report.power_budget) {
        powerGaugeVal.textContent = `~${report.power_budget.total_ma} mA`;
    }
    if (powerGaugeNote && report.power_budget) {
        if (report.power_budget.exceeds_usb) {
            powerGaugeNote.textContent = "Exceeds 500mA standard USB supply. Use external 5V 2A power adapter.";
            powerGaugeNote.style.color = "var(--warning-text)";
        } else {
            powerGaugeNote.textContent = "Safe to power directly from standard 500mA USB port.";
            powerGaugeNote.style.color = "var(--text-muted)";
        }
    }

    // 4. Pairwise Cards List
    const pairsContainer = document.getElementById("pairwise-checks-list");
    if (pairsContainer && report.pair_results) {
        let html = '<h3 class="pair-checks-heading">Pairwise Hardware Verification</h3>';

        if (report.pair_results.length === 0) {
            html += '<p style="color: var(--text-muted); font-size: 0.9rem;">No peripheral components in setup yet. Click "+ Add to Setup" on any recommended component.</p>';
        } else {
            report.pair_results.forEach(pair => {
                const statusBadgeClass = `badge-status-${pair.status}`;
                const statusBadgeText = pair.status === 'compatible' ? 'COMPATIBLE' : (pair.status === 'warning' ? 'WARNING' : 'INCOMPATIBLE');

                html += `
                    <div class="pair-check-card pair-status-${pair.status}">
                        <div class="pair-card-header">
                            <div class="pair-names">
                                <span class="chip-mcu">${escapeHtml(pair.component_a)}</span>
                                <span class="chip-arrow">/</span>
                                <span class="chip-peripheral">${escapeHtml(pair.component_b)}</span>
                            </div>
                            <span class="${statusBadgeClass}">${statusBadgeText}</span>
                        </div>

                        <div class="feature-checklist">
                            <span class="check-item ${pair.features.voltage ? 'item-ok' : 'item-warn'}">
                                ${pair.features.voltage ? 'PASS' : 'WARN'} Voltage
                            </span>
                            <span class="check-item ${pair.features.logic ? 'item-ok' : 'item-warn'}">
                                ${pair.features.logic ? 'PASS' : 'WARN'} Logic Level
                            </span>
                            <span class="check-item ${pair.features.interface ? 'item-ok' : 'item-fail'}">
                                ${pair.features.interface ? 'PASS' : 'FAIL'} Interface
                            </span>
                            <span class="check-item ${pair.features.pins ? 'item-ok' : 'item-fail'}">
                                ${pair.features.pins ? 'PASS' : 'FAIL'} Pins
                            </span>
                            <span class="check-item ${pair.features.current ? 'item-ok' : 'item-warn'}">
                                ${pair.features.current ? 'PASS' : 'WARN'} Current
                            </span>
                        </div>

                        <div class="pair-details-body">
                            <p class="pair-reason"><strong>Reason:</strong> ${escapeHtml(pair.reason)}</p>
                            ${pair.status !== 'compatible' ? `
                                <div class="pair-solution-callout">
                                    <strong>Suggested Solution:</strong> ${escapeHtml(pair.solution)}
                                </div>
                            ` : ''}
                        </div>

                        <div class="pair-footer">
                            <span class="ml-confidence">Confidence: <strong>${pair.ml_compatible_probability}%</strong></span>
                            <span class="decision-source">${escapeHtml(pair.decision_source)}</span>
                        </div>
                    </div>
                `;
            });
        }

        pairsContainer.innerHTML = html;
    }

    // 5. Hardware Pinout & Wiring Table Update
    if (report.wiring_guide) {
        currentWiringGuide = report.wiring_guide;
        
        // Update MCU subtitle
        const mcuSubtitle = document.getElementById("wiring-mcu-subtitle");
        if (mcuSubtitle) {
            mcuSubtitle.textContent = `Collision-free pin assignments, voltage rails, and signal routing for ${report.wiring_guide.mcu_name}.`;
        }

        // Update bus chips
        const busesRow = document.getElementById("wiring-buses-row");
        if (busesRow && report.wiring_guide.bus_summary) {
            const bus = report.wiring_guide.bus_summary;
            let busHtml = `
                <div class="bus-chip">
                    <strong>I2C Bus:</strong> SDA: ${escapeHtml(bus.i2c_bus.sda)} | SCL: ${escapeHtml(bus.i2c_bus.scl)}
                    ${bus.i2c_bus.devices.length > 0 ? `<span>(Shared: ${escapeHtml(bus.i2c_bus.devices.join(", "))})</span>` : ''}
                </div>
            `;
            if (bus.spi_bus && bus.spi_bus.devices.length > 0) {
                busHtml += `
                    <div class="bus-chip">
                        <strong>SPI Bus:</strong> MOSI: ${escapeHtml(bus.spi_bus.mosi)} | SCK: ${escapeHtml(bus.spi_bus.sck)}
                        <span>(Shared: ${escapeHtml(bus.spi_bus.devices.join(", "))})</span>
                    </div>
                `;
            }
            busesRow.innerHTML = busHtml;
        }

        // Update table body
        const tableBody = document.getElementById("wiring-table-body");
        if (tableBody && report.wiring_guide.wiring_table) {
            let tableHtml = "";
            report.wiring_guide.wiring_table.forEach(row => {
                tableHtml += `
                    <tr>
                        <td class="comp-name-cell">${escapeHtml(row.component_name)}</td>
                        <td><span class="pin-badge-peripheral">${escapeHtml(row.pin_label)}</span></td>
                        <td><span class="pin-badge-mcu">${escapeHtml(row.mcu_pin)}</span></td>
                        <td><span class="signal-type-tag">${escapeHtml(row.signal_type)}</span></td>
                        <td>
                            <span class="wire-color-tag">
                                <span class="wire-dot" style="background-color: ${escapeHtml(row.wire_hex)};"></span>
                                ${escapeHtml(row.wire_color)}
                            </span>
                        </td>
                        <td class="wiring-notes-cell">${escapeHtml(row.circuit_notes)}</td>
                    </tr>
                `;
            });
            tableBody.innerHTML = tableHtml;
        }

        // Update advisories
        const advisoryBox = document.getElementById("wiring-advisory-box");
        const advisoryList = document.getElementById("wiring-advisory-list");
        if (advisoryBox && advisoryList) {
            if (report.wiring_guide.advisories && report.wiring_guide.advisories.length > 0) {
                advisoryBox.style.display = "block";
                advisoryList.innerHTML = report.wiring_guide.advisories.map(a => `<li>${escapeHtml(a)}</li>`).join("");
            } else {
                advisoryBox.style.display = "none";
                advisoryList.innerHTML = "";
            }
        }
    }
}

/**
 * Copies the active wiring guide table to clipboard in Markdown format.
 */
async function copyWiringTable() {
    const btn = document.getElementById("btn-copy-wiring");
    const originalText = btn ? btn.textContent : "Copy Table (Markdown)";
    
    let textToCopy = "";
    if (currentWiringGuide && currentWiringGuide.export_markdown) {
        textToCopy = currentWiringGuide.export_markdown;
    } else {
        const rows = document.querySelectorAll("#wiring-table tbody tr");
        textToCopy = "| Component | Pin Label | Target MCU Pin | Signal Type | Wire Color | Electrical Notes |\n| :--- | :--- | :--- | :--- | :--- | :--- |\n";
        rows.forEach(tr => {
            const cells = Array.from(tr.querySelectorAll("td")).map(td => td.innerText.replace(/\n/g, " ").trim());
            if (cells.length >= 6) {
                textToCopy += `| ${cells[0]} | ${cells[1]} | ${cells[2]} | ${cells[3]} | ${cells[4]} | ${cells[5]} |\n`;
            }
        });
    }

    try {
        await navigator.clipboard.writeText(textToCopy);
        if (btn) {
            btn.textContent = "Table Copied!";
            btn.style.backgroundColor = "var(--color-sage-light)";
            btn.style.borderColor = "var(--color-sage)";
            btn.style.color = "var(--color-sage-dark)";
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.backgroundColor = "";
                btn.style.borderColor = "";
                btn.style.color = "";
            }, 2000);
        }
    } catch (e) {
        console.error("Clipboard copy failed:", e);
    }
}

/**
 * Downloads the active wiring guide as a formatted plain text file.
 */
async function downloadWiringGuide() {
    const platformElem = document.getElementById("active-platform");
    const platformId = platformElem ? (platformElem.dataset.platformId || "esp32") : "esp32";
    
    let content = "";
    if (currentWiringGuide && currentWiringGuide.export_text) {
        content = currentWiringGuide.export_text;
    } else {
        try {
            const resp = await fetch("/export-wiring", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    platform_id: platformId,
                    component_ids: activeSetupComponents
                })
            });
            content = await resp.text();
        } catch (e) {
            console.error("Download fetch failed:", e);
            return;
        }
    }

    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `wiring_guide_${platformId}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

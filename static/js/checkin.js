function clearForm() {
    window.location.href = "/checkin";
}

// 🔥 COMMON PNR FETCH (checkin + report दोनों के लिए)
function fetchPNR() {
    let pnr = document.getElementById("pnr").value;

    if (!pnr) return;

    // 1️⃣ basic details
    fetch(`/get-pnr/${pnr}`)
        .then(res => res.json())
        .then(data => {
            if (data.status) {

                if (document.getElementById("name"))
                    document.getElementById("name").value = data.data.name;

                if (document.getElementById("flight"))
                    document.getElementById("flight").value = data.data.flight;

                if (document.getElementById("destination"))
                    document.getElementById("destination").value = data.data.destination;

                if (document.getElementById("contact"))
                    document.getElementById("contact").value = data.data.contact;

                // 2️⃣ BAG ID fetch (report page)
                fetch(`/get-bag/${pnr}`)
                    .then(res => res.json())
                    .then(bag => {
                        if (bag.status && document.getElementById("bag_id")) {
                            document.getElementById("bag_id").value = bag.bag_id;
                        }
                    });

            } else {
                alert("Invalid PNR");
            }
        });
}


// 🔥 BAG WEIGHT (same as before - optimized)
function generateWeightFields() {
    let count = document.getElementById("bags").value;
    let container = document.getElementById("weightFields");

    container.innerHTML = "";

    if (count > 2) {
        alert("Max 2 bags allowed");
        document.getElementById("bags").value = 2;
        count = 2;
    }

    for (let i = 1; i <= count; i++) {
        container.innerHTML += `
            <div class="mb-2">
                <label>Weight of Bag ${i}</label>
                <input type="number" class="form-control bag-weight" oninput="calculateTotal()" required>
            </div>
        `;
    }
}

function calculateTotal() {
    let weights = document.querySelectorAll(".bag-weight");
    let total = 0;

    weights.forEach(w => {
        total += Number(w.value || 0);
    });

    let totalField = document.getElementById("totalWeight");
    totalField.value = total;

    if (total > 30) {
        alert("Total weight cannot exceed 30kg!");
        totalField.value = "";
    }
}
// js/index-ui.js

// Note: Dynamic data rendering (Featured, Trending, Categories, Ticker) 
// has been moved to js/homepage.js to fetch real data from the Django API.

// ==================== GLOBAL UI FUNCTIONALITY ====================

// // Update date/time in top bar
// function updateDateTime() {
//     const dateTimeEl = document.getElementById("dateTime");
//     if (dateTimeEl) {
//         const now = new Date();
//         dateTimeEl.innerText = now.toDateString() + " | " + now.toLocaleTimeString();
//     }
// }

// // Initial call and set interval
// updateDateTime();
// setInterval(updateDateTime, 1000);
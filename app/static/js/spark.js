// static/js/spark.js

// Function to get user ID from localStorage
function getUserID() {
  return localStorage.getItem("user_id") || 0;
}

// Function to set up the login handler
function handleUserLogin() {
  const loginButton = document.getElementById("login-button");
  const userIdInput = document.getElementById("user-id-input");

  if (loginButton && userIdInput) {
    loginButton.addEventListener("click", () => {
      const userId = userIdInput.value.trim();
      if (userId) {
        localStorage.setItem("user_id", userId);
        alert("User ID saved!");
        fetch(`/api/setCurrentUser?user_id=${userId}`, { method: "POST" })
          .then((response) => response.json())
          .then((data) => {
            console.log(data.message);
            location.reload(); // Refresh to apply the new user ID
          })
          .catch((error) =>
            console.error("Error setting current user:", error)
          );
      } else {
        alert("Please enter a valid User ID.");
      }
    });
  }
}

// Register event to all action buttons once the DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  // Attach event listeners for action buttons
  const likeButtons = document.getElementsByName("like");
  likeButtons.forEach((button) => {
    button.addEventListener("click", handleLike);
    button.setAttribute("tabindex", "0");
    button.setAttribute("role", "button");
  });

  const buyButtons = document.getElementsByName("buy");
  buyButtons.forEach((button) => {
    button.addEventListener("click", handleBuy);
    button.setAttribute("tabindex", "0");
    button.setAttribute("role", "button");
  });

  const rateButtons = document.getElementsByName("rate");
  rateButtons.forEach((button) => {
    button.addEventListener("click", handleRate);
    button.setAttribute("tabindex", "0");
    button.setAttribute("role", "button");
  });

  // Attach event listeners to product links for view tracking
  const productLinks = document.querySelectorAll(".product-view-link");
  productLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      const productId = link.getAttribute("data-pid"); // Fix by ensuring `link` reference
      const userId = getUserID();
      trackView(productId, userId);
    });
  });

  // Restore like status on load
  restoreLikeStatus();
});

// Track product view interaction
function trackView(productId, userId) {
  console.log("Product view:", productId, userId);
  sendInteraction("view", productId, userId);
}

// On DOMContentLoaded, set up event handlers and display the current user ID
document.addEventListener("DOMContentLoaded", function () {
  const currentUserId = getUserID();
  document.getElementById("user_id").textContent = currentUserId;

  handleUserLogin(); // Set up the login button handler

  // Additional code to handle product link clicks and user interactions
  const productLinks = document.querySelectorAll(".product-view-link");
  productLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      const productId = link.getAttribute("data-pid");
      trackView(productId, currentUserId);
    });
  });

  restoreLikeStatus(); // Restore like status on page load
});

// Like button handler
function handleLike(event) {
  const productId = event.target.getAttribute("data-pid");
  const userId = getUserID();
  const isLiked = toggleLike(event);

  // Set interaction value to 1 for like, 0 for unlike
  const value = isLiked ? 1 : 0;
  saveLikeStatus(productId, isLiked); // Persist like status
  sendInteraction("like", productId, userId, value);
}

// Save like status to localStorage for persisting per user and product
function saveLikeStatus(productId, isLiked) {
  const likes = JSON.parse(localStorage.getItem("likes") || "{}");
  likes[productId] = isLiked;
  localStorage.setItem("likes", JSON.stringify(likes));
}

// Restore like status from localStorage on load
function restoreLikeStatus() {
  const likes = JSON.parse(localStorage.getItem("likes") || "{}");
  const likeButtons = document.getElementsByName("like");
  likeButtons.forEach((button) => {
    const productId = button.getAttribute("data-pid");
    if (likes[productId]) {
      button.classList.add("like-on");
    }
  });
}

// Toggle like button style
function toggleLike(event) {
  const liked = event.target.classList.toggle("like-on");
  return liked;
}

// Buy button handler
function handleBuy(event) {
  const productId = event.target.getAttribute("data-pid");
  const userId = getUserID();
  sendInteraction("buy", productId, userId);
}

// Rate button handler
function handleRate(event) {
  const rating = parseInt(event.target.getAttribute("data-rating"), 10);
  const productId = event.target.getAttribute("data-pid");
  const userId = getUserID();
  updateRatingDisplay(rating, productId);
  sendInteraction("rate", productId, userId, null, rating);
}

// Update rating display stars
function updateRatingDisplay(rating, productId) {
  const rateButtons = document.querySelectorAll(
    `[data-pid="${productId}"][name="rate"]`
  );
  rateButtons.forEach((button, index) => {
    button.className = index < rating ? "star star-on" : "star";
  });
}

function fetchProductDetails(productId) {
  const userId = getUserID();
  fetch(`/api/product/${productId}?user_id=${userId}`)
    .then((response) => response.json())
    .then((data) => {
      console.log("Product details:", data);
      // Display or process the product details
    })
    .catch((error) => console.error("Error fetching product details:", error));
}

// Function to send interactions to the server
function sendInteraction(action, productId, value = null, reviewScore = null) {
  const userId = getUserID();
  const interactionData = {
    user_id: parseInt(userId, 10),
    product_id: parseInt(productId, 10),
    interaction_type: action,
    value: value,
    review_score: reviewScore,
  };

  fetch("/api/interaction", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(interactionData),
  })
    .then((response) => {
      if (!response.ok) {
        console.error("Error logging interaction:", response.statusText);
      } else {
        console.log("Interaction saved successfully");
      }
    })
    .catch((error) =>
      console.error("Network error logging interaction:", error)
    );
}

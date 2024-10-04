
// register event to all action buttons
document.addEventListener('DOMContentLoaded', function() {
    // add events to all action buttons
    const likeButtons = document.getElementsByName('like');
    for (let i = 0; i < likeButtons.length; i++) {
        likeButtons[i].addEventListener('click', toggleLike);
        likeButtons[i].setAttribute('tabindex', '0'); // Make div focusable
        likeButtons[i].setAttribute('role', 'button'); // Set role for accessibility
    }
});

// like button image toggle
function toggleLike(event) {
    const liked = event.target.classList.contains("like-on");
    event.target.className = liked ? "like" : "like like-on";
}

// add experience to database for RL
function addExperience(event) {
    target = event.target
    action = target.getAttribute("name")
    pid = target.getAttribute("data-pid")

    switch (action) {
        case "like":
            break;
        case "buy":
            break;
        case "view":
            break;
        case "rate":
            break;
        default:
            // do nothing
    }

}
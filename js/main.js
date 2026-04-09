const slider = document.querySelector(".featured-scroll");

slider.addEventListener("wheel", (event) => {
  event.preventDefault();
  slider.scrollLeft += event.deltaY;
});
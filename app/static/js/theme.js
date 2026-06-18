// 主题切换：在明暗之间切换并持久化到 localStorage。
// 首屏的初始主题由 base.html 头部内联脚本设置，避免闪烁。
function toggleTheme() {
	const root = document.documentElement;
	const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
	root.setAttribute("data-theme", next);
	localStorage.setItem("theme", next);
}

// 跟随系统：仅当用户未手动设置过主题时，响应系统偏好变化
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function (e) {
	if (!localStorage.getItem("theme")) {
		document.documentElement.setAttribute("data-theme", e.matches ? "dark" : "light");
	}
});

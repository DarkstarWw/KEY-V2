// 全站通用脚本：验证码倒计时、API 封装，以及评论 / 评分 / 收藏的 Alpine 组件工厂。

// ---------- 通用 API 封装 ----------
async function api(url, method = "GET", body = null) {
	const opts = { method, headers: {} };
	if (body !== null) {
		opts.headers["Content-Type"] = "application/json";
		opts.body = JSON.stringify(body);
	}
	const resp = await fetch(url, opts);
	return resp.json();
}

// ---------- 验证码按钮：发送 + 60 秒倒计时 ----------
document.addEventListener("DOMContentLoaded", function () {
	document.querySelectorAll(".code-btn").forEach(function (btn) {
		btn.addEventListener("click", async function () {
			const purpose = btn.dataset.purpose;
			const email = document.getElementById("email").value.trim();
			if (!email) {
				alert("请先填写邮箱");
				return;
			}
			btn.disabled = true;
			const res = await api("/api/send_code", "POST", { email: email, purpose: purpose });
			if (!res.ok) {
				alert(res.msg || "发送失败");
				btn.disabled = false;
				return;
			}
			let left = 60;
			btn.textContent = left + "s";
			const timer = setInterval(function () {
				left -= 1;
				if (left <= 0) {
					clearInterval(timer);
					btn.disabled = false;
					btn.textContent = "获取验证码";
				} else {
					btn.textContent = left + "s";
				}
			}, 1000);
		});
	});
});

// ---------- 评论组件（图组 / 单图通用，支持楼中楼） ----------
window.commentBox = function (targetType, targetId) {
	return {
		items: [],
		content: "",
		replyTo: null,
		replyName: "",
		async init() {
			await this.load();
		},
		async load() {
			const res = await api(`/api/comments?target_type=${targetType}&target_id=${targetId}`);
			if (res.ok) {
				this.items = res.items;
			}
		},
		// 顶层评论（无父）
		roots() {
			return this.items.filter((c) => !c.parent_id);
		},
		// 某条评论的子回复
		children(pid) {
			return this.items.filter((c) => c.parent_id === pid);
		},
		setReply(c) {
			this.replyTo = c.id;
			this.replyName = c.nickname;
		},
		cancelReply() {
			this.replyTo = null;
			this.replyName = "";
		},
		async submit() {
			if (!window.IS_AUTH) {
				alert("请先登录");
				return;
			}
			if (!this.content.trim()) {
				return;
			}
			const res = await api("/api/comment", "POST", {
				target_type: targetType,
				target_id: targetId,
				content: this.content,
				parent_id: this.replyTo,
			});
			if (res.ok) {
				this.content = "";
				this.cancelReply();
				await this.load();
			} else {
				alert(res.msg || "评论失败");
			}
		},
		async remove(id) {
			if (!confirm("确认删除该评论？")) {
				return;
			}
			const res = await api(`/api/comment/${id}/delete`, "POST");
			if (res.ok) {
				await this.load();
			} else {
				alert(res.msg || "删除失败");
			}
		},
	};
};

// ---------- 评分组件（单图 1-5 星） ----------
window.ratingBox = function (imageId) {
	return {
		avg: 0,
		count: 0,
		my: 0,
		hover: 0,
		items: [],
		showDetail: false,
		async init() {
			await this.load();
		},
		async load() {
			const res = await api(`/api/ratings?image_id=${imageId}`);
			if (res.ok) {
				this.avg = res.avg;
				this.count = res.count;
				this.my = res.my_score;
				this.items = res.items;
			}
		},
		async rate(score) {
			if (!window.IS_AUTH) {
				alert("请先登录");
				return;
			}
			const res = await api("/api/rate", "POST", { image_id: imageId, score: score });
			if (res.ok) {
				await this.load();
			} else {
				alert(res.msg || "评分失败");
			}
		},
	};
};

// ---------- 收藏按钮（图组 / 单图通用） ----------
window.favBox = function (targetType, targetId) {
	return {
		fav: false,
		async init() {
			if (!window.IS_AUTH) {
				return;
			}
			const res = await api(
				`/api/favorite/status?target_type=${targetType}&target_id=${targetId}`
			);
			if (res.ok) {
				this.fav = res.favorited;
			}
		},
		async toggle() {
			if (!window.IS_AUTH) {
				alert("请先登录");
				return;
			}
			const res = await api("/api/favorite", "POST", {
				target_type: targetType,
				target_id: targetId,
			});
			if (res.ok) {
				this.fav = res.favorited;
			}
		},
	};
};

// ---------- 后台：用户权限搜索弹窗（站长专用） ----------
window.adminPicker = function () {
	return {
		open: false,
		q: "",
		loading: false,
		results: [],
		async search() {
			const kw = this.q.trim();
			if (!kw) {
				this.results = [];
				this.loading = false;
				return;
			}
			this.loading = true;
			const res = await api(`/admin/search_users?q=${encodeURIComponent(kw)}`);
			this.loading = false;
			this.results = (res && res.items) || [];
		},
		async setRole(user, role) {
			const verb = role === "admin" ? "设为管理员" : "撤销管理员";
			if (!confirm(`确认对「${user.nickname}」执行：${verb}？`)) {
				return;
			}
			const resp = await fetch("/admin/role", {
				method: "POST",
				headers: { "Content-Type": "application/x-www-form-urlencoded" },
				body: `user_id=${user.id}&role=${role}`,
			});
			if (resp.ok) {
				user.role = role;
				location.reload();
			} else {
				alert("操作失败");
			}
		},
	};
};

// ---------- 首页/分类：左下角全站用户列表面板 ----------
window.userPanel = function () {
	return {
		open: false,
		loading: false,
		page: 1,
		pages: 1,
		total: 0,
		users: [],
		roleLabel(role) {
			if (role === "owner") return "站长";
			if (role === "admin") return "管理员";
			return "用户";
		},
		toggle() {
			this.open = !this.open;
			if (this.open && this.users.length === 0) {
				this.load(1);
			}
		},
		async load(page) {
			this.loading = true;
			const res = await api(`/api/users?page=${page}`);
			this.loading = false;
			this.users = (res && res.items) || [];
			this.page = (res && res.page) || 1;
			this.pages = (res && res.pages) || 1;
			this.total = (res && res.total) || 0;
		},
		prev() {
			if (this.page > 1) {
				this.load(this.page - 1);
			}
		},
		next() {
			if (this.page < this.pages) {
				this.load(this.page + 1);
			}
		},
	};
};

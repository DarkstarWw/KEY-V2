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
		editingId: null,
		editContent: "",
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
		// 编辑评论（仅站长 / 管理员）
		startEdit(c) {
			this.editingId = c.id;
			this.editContent = c.content;
		},
		cancelEdit() {
			this.editingId = null;
			this.editContent = "";
		},
		async saveEdit(id) {
			if (!this.editContent.trim()) {
				return;
			}
			const res = await api(`/api/comment/${id}/edit`, "POST", { content: this.editContent });
			if (res.ok) {
				this.cancelEdit();
				await this.load();
			} else {
				alert(res.msg || "修改失败");
			}
		},
	};
};

// ---------- 图组详情：大图查看（含左右切换）+ 管理员就地编辑 ----------
window.galleryDetail = function (cfg) {
	return {
		// 大图查看
		lb: false,
		curId: null,
		ids: cfg.ids,
		open(id) {
			this.curId = id;
			this.lb = true;
			document.body.style.overflow = "hidden";
		},
		close() {
			this.lb = false;
			this.curId = null;
			document.body.style.overflow = "";
		},
		idx() {
			return this.ids.indexOf(this.curId);
		},
		prev() {
			const i = this.idx();
			if (i > 0) {
				this.curId = this.ids[i - 1];
			}
		},
		next() {
			const i = this.idx();
			if (i < this.ids.length - 1) {
				this.curId = this.ids[i + 1];
			}
		},
		// 就地编辑（仅站长 / 管理员）
		gid: cfg.gid,
		editing: false,
		saving: false,
		form: { title: cfg.title, description: cfg.description, category: cfg.category },
		toggleEdit() {
			this.editing = !this.editing;
			if (this.editing) {
				this.form = {
					title: cfg.title,
					description: cfg.description,
					category: cfg.category,
				};
			}
		},
		async saveMeta() {
			if (!this.form.title.trim()) {
				alert("标题不能为空");
				return;
			}
			this.saving = true;
			const res = await api(`/gallery/${this.gid}/update`, "POST", {
				title: this.form.title,
				description: this.form.description,
				category: this.form.category,
			});
			this.saving = false;
			if (res.ok) {
				location.reload();
			} else {
				alert(res.msg || "保存失败");
			}
		},
		async setCover(imageId) {
			const res = await api(`/gallery/${this.gid}/cover`, "POST", { image_id: imageId });
			if (res.ok) {
				location.reload();
			} else {
				alert(res.msg || "设置封面失败");
			}
		},
		async delImage(imageId) {
			if (!confirm("确认删除这张图片？")) {
				return;
			}
			const res = await api(`/gallery/${this.gid}/image/${imageId}/delete`, "POST");
			if (res.ok) {
				location.reload();
			} else {
				alert(res.msg || "删除失败");
			}
		},
		async addImages(event) {
			const input = event.target;
			if (!input.files || input.files.length === 0) {
				return;
			}
			const fd = new FormData();
			for (const f of input.files) {
				fd.append("images", f);
			}
			this.saving = true;
			const resp = await fetch(`/gallery/${this.gid}/images`, { method: "POST", body: fd });
			const res = await resp.json();
			this.saving = false;
			if (res.ok) {
				location.reload();
			} else {
				alert(res.msg || "上传失败");
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

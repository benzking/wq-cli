import { ref, readonly, computed } from 'vue'
import DOMPurify from 'dompurify'

export function useArticles() {
  const subscriptions = ref([])
  const selectedFakeid = ref('')
  const articles = ref([])
  const currentArticle = ref(null)
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(20)
  const keyword = ref('')
  const loading = ref(false)
  const detailLoading = ref(false)

  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / perPage.value)))

  async function loadSubscriptions() {
    try {
      const res = await fetch('/api/browse/subscriptions')
      const data = await res.json()
      if (data.success) { subscriptions.value = data.data.subscriptions || [] }
    } catch {}
  }

  async function loadArticles() {
    loading.value = true
    try {
      const params = new URLSearchParams({
        page: page.value,
        per_page: perPage.value,
      })
      if (selectedFakeid.value) params.set('fakeid', selectedFakeid.value)
      if (keyword.value) params.set('keyword', keyword.value)

      const res = await fetch(`/api/browse/articles?${params}`)
      const data = await res.json()
      if (data.success) {
        articles.value = data.data.articles || []
        total.value = data.data.total || 0
        page.value = data.data.page || 1
      }
    } finally {
      loading.value = false
    }
  }

  async function loadArticleDetail(id) {
    detailLoading.value = true
    try {
      const res = await fetch(`/api/browse/article/${id}`)
      const data = await res.json()
      if (data.success) {
        const article = data.data.article
        if (article.content) {
          article.content = DOMPurify.sanitize(article.content, {
            ALLOWED_TAGS: ['p', 'br', 'strong', 'b', 'em', 'i', 'a', 'img', 'h1', 'h2', 'h3',
              'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'pre', 'code', 'span', 'div',
              'table', 'thead', 'tbody', 'tr', 'td', 'th', 'section', 'figure',
              'figcaption', 'video', 'source', 'hr', 'sub', 'sup', 'caption', 'col', 'colgroup'],
            ALLOWED_ATTR: ['href', 'src', 'alt', 'class', 'id', 'width', 'height',
              'style', 'data-*', 'target', 'title', 'loading'],
          })
        }
        currentArticle.value = article
      }
    } finally {
      detailLoading.value = false
    }
  }

  async function toggleStar(id) {
    await fetch(`/api/browse/article/${id}/star`, { method: 'PATCH' })
    if (currentArticle.value && currentArticle.value.id === id) {
      currentArticle.value = { ...currentArticle.value, starred: currentArticle.value.starred ? 0 : 1 }
    }
  }

  function selectFakeid(fakeid) {
    selectedFakeid.value = fakeid
    page.value = 1
    keyword.value = ''
    currentArticle.value = null
    loadArticles()
  }

  function changePage(p) {
    page.value = p
    loadArticles()
  }

  function search(kw) {
    keyword.value = kw
    page.value = 1
    loadArticles()
  }

  return {
    subscriptions: readonly(subscriptions),
    selectedFakeid: readonly(selectedFakeid),
    articles: readonly(articles),
    currentArticle: readonly(currentArticle),
    total: readonly(total),
    page: readonly(page),
    keyword: readonly(keyword),
    totalPages,
    loading: readonly(loading),
    detailLoading: readonly(detailLoading),
    loadSubscriptions,
    loadArticles,
    loadArticleDetail,
    toggleStar,
    selectFakeid,
    changePage,
    search,
  }
}

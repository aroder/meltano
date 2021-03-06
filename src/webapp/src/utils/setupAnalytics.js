import Vue from 'vue'

import VueAnalytics from 'vue-analytics'

export default function setup({ id, router }) {
  const isDisabled =
    'hasDisabledTracking' in localStorage &&
    localStorage.getItem('hasDisabledTracking') === 'true'

  if (!isDisabled) {
    Vue.use(VueAnalytics, {
      id,
      router,
      set: [
        {
          // Unfortunately custom dimensions don't allow a useful alias, dimension1 is projectId
          field: 'dimension1',
          value: Vue.prototype.$flask.projectId
        },
        {
          // Unfortunately custom dimensions don't allow a useful alias, dimension2 is the Meltano app version
          field: 'dimension2',
          value: Vue.prototype.$flask.version
        }
      ]
    })
  }
}

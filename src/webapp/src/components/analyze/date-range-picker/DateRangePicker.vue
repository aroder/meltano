<script>
import { mapActions, mapGetters } from 'vuex'

import lodash from 'lodash'

import DateRangePickerHeader from '@/components/analyze/date-range-picker/DateRangePickerHeader'
import Dropdown from '@/components/generic/Dropdown'
import { EVENTS } from '@/components/analyze/date-range-picker/events'
import {
  getDateLabel,
  getHasValidDateRange,
  getNullDateRange,
  getDateRangesForAttributeFilters
} from '@/components/analyze/date-range-picker/utils'
import { QUERY_ATTRIBUTE_TYPES } from '@/api/design'
import utils from '@/utils/utils'

export default {
  name: 'DateRangePicker',
  components: {
    DateRangePickerHeader,
    Dropdown
  },
  props: {
    attributes: { type: Array, required: true },
    filters: { type: Array, default: () => [] }
  },
  data: () => ({
    attributePairsModel: [],
    attributePairInFocusIndex: 0,
    hasSetAttributePairInFocusIndex: false
  }),
  computed: {
    ...mapGetters('designs', ['getFilters', 'getIsDateAttribute']),
    getAttributePairInFocus() {
      return this.attributePairsModel[this.attributePairInFocusIndex]
    },
    getAttributePairsInitial() {
      return this.attributes.map(attribute => {
        const filters = this.getFilters(attribute)
        return {
          attribute,
          ...getDateRangesForAttributeFilters(filters)
        }
      })
    },
    getCalendarAttributes() {
      return [
        {
          key: 'today',
          bar: true,
          popover: {
            label: 'Today'
          },
          dates: new Date()
        }
      ]
    },
    getDateFilters() {
      return this.filters.filter(filter =>
        this.getIsDateAttribute(filter.attribute)
      )
    },
    getDateLabel() {
      return getDateLabel
    },
    getHasValidDateRange() {
      return getHasValidDateRange
    },
    getIsAttributePairInFocus() {
      return attributePair =>
        attributePair ===
        this.attributePairsModel[this.attributePairInFocusIndex]
    },
    getIsSavable() {
      const mapper = attributePair => attributePair.absoluteDateRange
      const initialDateRanges = this.getAttributePairsInitial.map(mapper)
      const modelDateRanges = this.attributePairsModel.map(mapper)
      return !lodash.isEqual(initialDateRanges, modelDateRanges)
    },
    getHasMultipleDateRanges() {
      return this.attributes.length > 1
    },
    getKey() {
      return utils.key
    },
    getLabel() {
      const validDateRangeLength = this.getValidDateRangesInitial.length
      const hasValidDateRanges = validDateRangeLength > 0
      let rangeLabel
      if (hasValidDateRanges) {
        rangeLabel = this.getDateLabel(
          this.getValidDateRangesInitial[0].absoluteDateRange
        )
        if (validDateRangeLength > 1) {
          rangeLabel += ` (+${validDateRangeLength - 1})`
        }
      }
      const fallbackLabel = `Date Range${
        this.getHasMultipleDateRanges ? 's' : ''
      }`
      return hasValidDateRanges ? rangeLabel : fallbackLabel
    },
    getValidDateRangesInitial() {
      return this.getAttributePairsInitial.filter(attributePair =>
        this.getHasValidDateRange(attributePair.absoluteDateRange)
      )
    }
  },
  created() {
    this.$root.$on(EVENTS.CHANGE_DATE_RANGE, this.onChangeDateRange)
  },
  beforeDestroy() {
    this.$root.$off(EVENTS.CHANGE_DATE_RANGE, this.onChangeDateRange)
  },
  methods: {
    ...mapActions('designs', ['addFilter', 'removeFilter']),
    onDayClick() {
      if (this.getAttributePairInFocus.isRelative) {
        this.onClearDateRange(this.getAttributePairInFocus)
        this.$root.$emit(EVENTS.CHANGE_DATE_RANGE, {
          isRelative: false,
          relativeDateRange: getNullDateRange(),
          absoluteDateRange: getNullDateRange()
        })
      }
    },
    onChangeAttributePairInFocus(attributePair) {
      this.attributePairInFocusIndex = this.attributePairsModel.indexOf(
        attributePair
      )
    },
    onChangeDateRange(payload) {
      const attributePairInFocus = this.getAttributePairInFocus
      const priorIsRelative = attributePairInFocus.isRelative
      attributePairInFocus.isRelative = payload.isRelative
      attributePairInFocus.relativeDateRange = payload.relativeDateRange

      // Conditionally apply priorCustomDateRange and update absoluteDateRange if applicable
      if (payload.isRelative) {
        const hasPrior =
          attributePairInFocus.priorCustomDateRange.start !== null
        // Only apply a priorCustomDateRange update when returning to custom from relative mode and only if no prior value exists
        if (!hasPrior && !priorIsRelative) {
          attributePairInFocus.priorCustomDateRange = Object.assign(
            {},
            attributePairInFocus.absoluteDateRange
          )
        }
        attributePairInFocus.absoluteDateRange = payload.absoluteDateRange
      } else {
        attributePairInFocus.absoluteDateRange = Object.assign(
          {},
          attributePairInFocus.priorCustomDateRange
        )
        attributePairInFocus.priorCustomDateRange = getNullDateRange()
      }
    },
    onClearDateRange(attributePair) {
      attributePair.absoluteDateRange = getNullDateRange()
      attributePair.priorCustomDateRange = getNullDateRange()
      attributePair.isRelative = false
    },
    onDropdownOpen(payload) {
      this.attributePairsModel = lodash.cloneDeep(this.getAttributePairsInitial)
      this.setInitialAttributePairInFocusIndex(payload)
    },
    setInitialAttributePairInFocusIndex(payload) {
      let match
      let idx
      // Set the target index based on an optional payload or first date range match condition or 0 index fallback
      if (payload) {
        match = this.attributePairsModel.find(
          attributePair => attributePair.attribute.key === payload.key
        )
      } else if (!this.hasSetAttributePairInFocusIndex) {
        match = this.attributePairsModel.find(
          attributePair => attributePair.absoluteDateRange.start !== null
        )
        this.hasSetAttributePairInFocusIndex = true
      }
      idx = match ? this.attributePairsModel.indexOf(match) : 0
      this.attributePairInFocusIndex = idx
    },
    saveDateRanges() {
      this.attributePairsModel.forEach(attributePair => {
        const {
          attribute,
          isRelative,
          absoluteDateRange,
          relativeDateRange
        } = attributePair
        const partialShared = {
          attribute: attribute,
          filterType: QUERY_ATTRIBUTE_TYPES.COLUMN
        }

        let startValue = absoluteDateRange.start || null
        let endValue = absoluteDateRange.end || null
        if (isRelative) {
          startValue = relativeDateRange.start
          endValue = relativeDateRange.end
        } else {
          if (startValue) {
            startValue = utils.formatDateStringYYYYMMDD(startValue)
            if (attribute.type === 'time') {
              startValue += 'T00:00:00.000Z'
            }
          }
          if (endValue) {
            endValue = utils.formatDateStringYYYYMMDD(endValue)
            if (attribute.type === 'time') {
              endValue += 'T23:59:59.999Z'
            }
          }
        }

        const partialStart = {
          expression: 'greater_or_equal_than', // TODO refactor `filterOptions` and/or constants approach
          value: startValue
        }
        const partialEnd = {
          expression: 'less_or_equal_than', // TODO refactor `filterOptions` and/or constants approach
          value: endValue
        }

        // Apply filters as a pair
        const filters = this.getFilters(attribute)
        const startFilter = filters.find(
          filter => filter.expression === partialStart.expression
        )
        const endFilter = filters.find(
          filter => filter.expression === partialEnd.expression
        )

        // Always remove before conditionally adding for simplicity (removes need for an `updateFilter()` at negligable perf cost)
        const hasFilters = filters.length > 0
        if (hasFilters) {
          this.removeFilter(startFilter)
          this.removeFilter(endFilter)
        }

        const isAdd = partialStart.value !== null && partialEnd.value !== null
        if (isAdd) {
          this.addFilter(Object.assign(partialStart, partialShared))
          this.addFilter(Object.assign(partialEnd, partialShared))
        }
      })
    }
  }
}
</script>

<template>
  <Dropdown
    ref="date-range-dropdown"
    :label="getLabel"
    menu-classes="dropdown-menu-600"
    :button-classes="
      `${
        getValidDateRangesInitial.length > 0
          ? 'has-text-interactive-secondary'
          : ''
      }`
    "
    is-right-aligned
    icon-open="calendar"
    @dropdown:open="onDropdownOpen"
  >
    <div class="dropdown-content">
      <!-- Picker Header -->
      <div v-if="getAttributePairInFocus" class="dropdown-item">
        <DateRangePickerHeader
          :attribute-pair="getAttributePairInFocus"
          :attribute-pairs-model="attributePairsModel"
          @attribute-pair-change="onChangeAttributePairInFocus"
          @clear-date-range="onClearDateRange"
        />
      </div>

      <!-- Picker Body -->
      <template v-for="attributePair in attributePairsModel">
        <div
          v-if="getIsAttributePairInFocus(attributePair)"
          :key="attributePair.attribute.key"
          class="dropdown-item"
        >
          <v-date-picker
            v-model="attributePair.absoluteDateRange"
            class="v-calendar-theme"
            mode="range"
            is-expanded
            is-inline
            :columns="2"
            :attributes="getCalendarAttributes"
            @dayclick="onDayClick"
          />
        </div>
      </template>

      <!-- Picker Footer -->
      <div class="dropdown-item">
        <div class="buttons is-right">
          <button class="button is-text" data-dropdown-auto-close>
            Cancel
          </button>
          <button
            class="button"
            :disabled="!getIsSavable"
            data-dropdown-auto-close
            @click="saveDateRanges"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  </Dropdown>
</template>

<style lang="scss">
/* TODO refactor with proper themeing (font and is-interactive-secondary color) when guide is udpated https://vcalendar.io/theming-guide.html */
.v-calendar-theme {
  font-family: $family-sans-serif;
}
</style>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { LMap, LTileLayer, LPolyline, LCircleMarker, LTooltip } from '@vue-leaflet/vue-leaflet'
import { latLngBounds, type LatLngExpression, type Map as LeafletMap } from 'leaflet'
import type { RoutePlanResponse } from '../../types/api'

const props = withDefaults(
  defineProps<{
    plan?: RoutePlanResponse | null
    initialCenter?: [number, number]
    initialZoom?: number
  }>(),
  {
    plan: null,
    initialCenter: () => [39.9042, 116.4074] as [number, number],
    initialZoom: 14,
  }
)

const tileUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const tileAttribution = '地图数据 © OpenStreetMap 贡献者'

const mapInstance = ref<LeafletMap | null>(null)

const nodePoints = computed(() =>
  (props.plan?.nodes ?? [])
    .filter((node) => Number.isFinite(node.latitude) && Number.isFinite(node.longitude))
    .map((node, index) => ({
      id: node.id,
      label: node.name ?? `节点 ${node.id}`,
      coords: [node.latitude, node.longitude] as [number, number],
      order: index + 1,
    }))
)

const polylinePoints = computed(() => nodePoints.value.map((node) => node.coords))
const startNodeId = computed(() => nodePoints.value[0]?.id ?? null)
const endNodeId = computed(() => nodePoints.value[nodePoints.value.length - 1]?.id ?? null)

const bounds = computed(() => {
  if (!nodePoints.value.length) {
    return null
  }
  return latLngBounds(nodePoints.value.map((point) => point.coords) as LatLngExpression[])
})

const mapCenter = computed<[number, number]>(() => {
  const currentBounds = bounds.value
  if (currentBounds) {
    const center = currentBounds.getCenter()
    return [center.lat, center.lng]
  }
  return props.initialCenter
})

const fitToCurrentBounds = () => {
  const map = mapInstance.value
  const targetBounds = bounds.value
  if (!map || !targetBounds) return

  const panes = map.getPanes()
  if (!panes || !panes.mapPane) {
    return
  }

  nextTick(() => {
    if (map !== mapInstance.value) return

    map.invalidateSize()
    map.fitBounds(targetBounds, { padding: [40, 40] })
  })
}

watch([bounds, () => mapInstance.value], () => {
  fitToCurrentBounds()
})

const handleReady = (map: LeafletMap) => {
  mapInstance.value = map
  fitToCurrentBounds()
}

const mapKey = computed(() => props.plan?.generated_at ?? `default-${props.plan?.region_id ?? 'map'}`)

const hasRoute = computed(() => nodePoints.value.length > 1)

watch(
  () => mapKey.value,
  () => {
    mapInstance.value = null
  }
)

const handleResize = () => {
  if (!mapInstance.value) return
  fitToCurrentBounds()
}

onMounted(() => {
  if (typeof window === 'undefined') return
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  if (typeof window === 'undefined') return
  window.removeEventListener('resize', handleResize)
})
</script>

<template>
  <div class="map-card">
    <div class="map-viewport">
      <LMap
        :key="mapKey"
        class="map-canvas"
        :center="mapCenter"
        :zoom="props.initialZoom"
        :zoom-control="false"
        @ready="handleReady"
      >
      <LTileLayer :url="tileUrl" :attribution="tileAttribution" />

      <LPolyline
        v-if="polylinePoints.length"
        :lat-lngs="polylinePoints"
        color="#2563eb"
        :weight="5"
        :opacity="0.9"
        :line-cap="'round'"
      />

      <LCircleMarker
        v-for="node in nodePoints"
        :key="node.id"
        :lat-lng="node.coords"
        :radius="node.id === startNodeId || node.id === endNodeId ? 8 : 6"
        :color="node.id === startNodeId ? '#16a34a' : node.id === endNodeId ? '#dc2626' : '#1d4ed8'"
        :fill-color="node.id === startNodeId ? '#4ade80' : node.id === endNodeId ? '#f87171' : '#3b82f6'"
        :fill-opacity="0.95"
        :weight="2"
      >
        <LTooltip>
          <div class="tooltip">
            <span class="order">#{{ node.order }}</span>
            <span>{{ node.label }}</span>
          </div>
        </LTooltip>
      </LCircleMarker>
      </LMap>
    </div>
    <div v-if="!nodePoints.length" class="map-placeholder">
      <span class="placeholder-title">等待路线数据</span>
      <span class="placeholder-copy">填写参数并点击「计算路线」，即可在地图上查看路径。</span>
    </div>
    <div v-else-if="!hasRoute" class="map-placeholder">
      <span class="placeholder-title">缺少完整路径</span>
      <span class="placeholder-copy">后端尚未返回完整的节点序列。</span>
    </div>
    <div class="map-legend">
      <span class="legend-item legend-start">起点</span>
      <span class="legend-item legend-end">终点</span>
      <span class="legend-item legend-path">路径</span>
    </div>
  </div>
</template>

<style scoped>
.map-card {
  position: relative;
  border-radius: 1rem;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(248, 250, 252, 0.85));
  overflow: hidden;
  box-shadow: 0 20px 45px -20px rgba(15, 23, 42, 0.35);
}

.map-viewport {
  position: relative;
  height: 420px;
  width: 100%;
}

.map-viewport :deep(.leaflet-container) {
  height: 100%;
  width: 100%;
}

.map-viewport :deep(.leaflet-control-container .leaflet-control-attribution) {
  font-size: 12px;
}

.map-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.65), rgba(241, 245, 249, 0.45));
  text-align: center;
  color: #475569;
  pointer-events: none;
}

.placeholder-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1e293b;
}

.placeholder-copy {
  font-size: 0.8rem;
}

.map-legend {
  position: absolute;
  bottom: 16px;
  right: 16px;
  display: flex;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 9999px;
  background-color: rgba(15, 23, 42, 0.76);
  color: white;
  font-size: 12px;
  letter-spacing: 0.01em;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.legend-item::before {
  content: '';
  display: inline-flex;
  width: 10px;
  height: 10px;
  border-radius: 9999px;
  background-color: currentColor;
}

.legend-start {
  color: #22c55e;
}

.legend-end {
  color: #ef4444;
}

.legend-path::before {
  width: 18px;
  height: 4px;
  border-radius: 9999px;
  background-color: #3b82f6;
}

.tooltip {
  display: flex;
  flex-direction: column;
  font-size: 0.75rem;
  gap: 0.15rem;
}

.order {
  font-weight: 600;
  color: #1d4ed8;
}
</style>

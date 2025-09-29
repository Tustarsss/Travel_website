<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { LMap, LTileLayer, LPolyline, LCircleMarker, LTooltip, LGeoJson } from '@vue-leaflet/vue-leaflet'
import {
  circleMarker,
  latLngBounds,
  type GeoJSONOptions,
  type LatLngExpression,
  type Map as LeafletMap,
} from 'leaflet'
import type { Feature, FeatureCollection, Geometry } from 'geojson'
import type { FacilityRouteItem, RoutePlanResponse } from '../../types/api'

const props = withDefaults(
  defineProps<{
    plan?: RoutePlanResponse | null
    tile?: FeatureCollection | null
    loading?: boolean
    facilities?: FacilityRouteItem[]
    initialCenter?: [number, number]
    initialZoom?: number
    showRoads?: boolean
  }>(),
  {
    plan: null,
    tile: null,
    loading: false,
    facilities: () => [],
    initialCenter: () => [39.9042, 116.4074] as [number, number],
    initialZoom: 14,
    showRoads: false,
  }
)

const tileUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const tileAttribution = '地图数据 © OpenStreetMap 贡献者'

const mapInstance = ref<LeafletMap | null>(null)

const nodeMap = computed(() =>
  new Map(
    (props.plan?.nodes ?? [])
      .filter((node) => Number.isFinite(node.latitude) && Number.isFinite(node.longitude))
      .map((node) => [node.id, node])
  )
)

const nodePoints = computed((): Array<{
  id: number
  label: string
  coords: [number, number]
  order: number
}> => {
  const allNodes = (props.plan?.nodes ?? [])
    .filter((node) => Number.isFinite(node.latitude) && Number.isFinite(node.longitude))
    .map((node, index) => ({
      id: node.id,
      label: node.name ?? `节点 ${node.id}`,
      coords: [node.latitude, node.longitude] as [number, number],
      order: index + 1,
    }))

  // 显示所有路线节点（起始点、目标点、途径路线上的所有节点）
  return allNodes
})
const startNodeId = computed(() => nodePoints.value[0]?.id ?? null)
const endNodeId = computed(() => nodePoints.value[nodePoints.value.length - 1]?.id ?? null)

const facilityPoints = computed(() =>
  (props.facilities ?? [])
    .filter((item) => Number.isFinite(item.latitude) && Number.isFinite(item.longitude))
    .map((item) => ({
      id: item.facility_id,
      label: item.name,
      coords: [item.latitude, item.longitude] as [number, number],
      distance: item.distance,
      travelTime: item.travel_time,
      category: item.category,
    }))
)

const boundsFromNodes = computed(() => {
  if (!nodePoints.value.length) {
    return null
  }
  return latLngBounds(nodePoints.value.map((point) => point.coords) as LatLngExpression[])
})

const MODE_STYLES: Record<string, { color: string; weight: number }> = {
  walk: { color: '#2563eb', weight: 5 },
  bike: { color: '#ea580c', weight: 5 },
  electric_cart: { color: '#9333ea', weight: 5 },
}

const segmentPolylines = computed(() => {
  if (!props.plan) return []

  return (props.plan.segments ?? [])
    .map((segment, index) => {
      const start = nodeMap.value.get(segment.source_id)
      const end = nodeMap.value.get(segment.target_id)
      if (!start || !end) return null

      const mode = segment.transport_mode?.toLowerCase?.() ?? 'walk'
      const style = MODE_STYLES[mode] ?? { color: '#2563eb', weight: 5 }

      return {
        key: `${segment.source_id}-${segment.target_id}-${mode}-${index}`,
        coords: [
          [start.latitude, start.longitude] as [number, number],
          [end.latitude, end.longitude] as [number, number],
        ],
        color: style.color,
        weight: style.weight,
        mode,
      }
    })
    .filter((segment): segment is {
      key: string
      coords: [number, number][]
      color: string
      weight: number
      mode: string
    } => Boolean(segment))
})

const legendModes = computed(() => {
  const unique = new Map<string, { color: string; label: string }>()
  for (const segment of segmentPolylines.value) {
    if (unique.has(segment.mode)) continue
    const style = MODE_STYLES[segment.mode] ?? { color: '#2563eb', weight: 5 }
    const label =
      segment.mode === 'bike'
        ? '骑行'
        : segment.mode === 'electric_cart'
          ? '电瓶车'
          : '步行'
    unique.set(segment.mode, { color: style.color, label })
  }
  return Array.from(unique.entries()).map(([mode, meta]) => ({ mode, ...meta }))
})

const boundsFromFacilities = computed(() => {
  if (!facilityPoints.value.length) {
    return null
  }
  return latLngBounds(facilityPoints.value.map((point) => point.coords) as LatLngExpression[])
})

const filteredTile = computed(() => {
  if (!props.tile) return undefined
  if (props.showRoads) return props.tile

  // 当不显示道路时，不显示任何地图要素
  return undefined
})

type LatLngTuple = [number, number]
type Coordinate = [number, number] | [number, number, number]

const geometryToLatLngs = (geometry: Geometry | null | undefined): LatLngTuple[] => {
  if (!geometry) return []

  const toLatLng = (coord: Coordinate): LatLngTuple => [coord[1], coord[0]]

  switch (geometry.type) {
    case 'Point':
      return [toLatLng(geometry.coordinates as Coordinate)]
    case 'MultiPoint':
      return geometry.coordinates.map((coord) => toLatLng(coord as Coordinate))
    case 'LineString':
      return geometry.coordinates.map((coord) => toLatLng(coord as Coordinate))
    case 'MultiLineString':
      return geometry.coordinates.flatMap((coords) =>
        coords.map((coord) => toLatLng(coord as Coordinate))
      )
    case 'Polygon':
      return geometry.coordinates.flatMap((ring) =>
        ring.map((coord) => toLatLng(coord as Coordinate))
      )
    case 'MultiPolygon':
      return geometry.coordinates.flatMap((polygon) =>
        polygon.flatMap((ring) => ring.map((coord) => toLatLng(coord as Coordinate)))
      )
    case 'GeometryCollection':
      return geometry.geometries.flatMap((child) => geometryToLatLngs(child))
    default:
      return []
  }
}

const boundsFromTile = computed(() => {
  if (!filteredTile.value) return null
  const coords = filteredTile.value.features.flatMap((feature: Feature) =>
    geometryToLatLngs(feature.geometry)
  )
  if (!coords.length) return null
  return latLngBounds(coords as LatLngExpression[])
})

const activeBounds = computed(() =>
  boundsFromNodes.value ?? boundsFromFacilities.value ?? boundsFromTile.value
)

const mapCenter = computed<[number, number]>(() => {
  const currentBounds = activeBounds.value
  if (currentBounds) {
    const center = currentBounds.getCenter()
    return [center.lat, center.lng]
  }
  return props.initialCenter
})

const fitToCurrentBounds = () => {
  const map = mapInstance.value
  const targetBounds = activeBounds.value
  if (!map || !targetBounds) return

  const panes = map.getPanes()
  if (!panes || !panes.mapPane) return

  nextTick(() => {
    if (map !== mapInstance.value) return
    map.invalidateSize()
    map.fitBounds(targetBounds, { padding: [40, 40] })
  })
}

watch([activeBounds, () => mapInstance.value], () => {
  fitToCurrentBounds()
})

const handleReady = (map: LeafletMap) => {
  mapInstance.value = map
  fitToCurrentBounds()
}

const tileSignature = computed(() => {
  if (!props.tile) return 'no-tile'
  const featureCount = props.tile.features?.length ?? 0
  const extent = boundsFromTile.value?.toBBoxString() ?? 'no-bounds'
  return `tile-${featureCount}-${extent}`
})

const mapKey = computed(
  () => props.plan?.generated_at ?? `${props.plan?.region_id ?? 'region'}-${tileSignature.value}`
)

const hasRoute = computed(() => segmentPolylines.value.length > 0)
const hasFacilities = computed(() => facilityPoints.value.length > 0)

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

const geoJsonOptions: GeoJSONOptions = {
  style: (feature) => {
    const featureType = ((feature?.properties ?? {}) as Record<string, unknown>).feature_type
    if (featureType === 'edge') {
      return { color: '#94a3b8', weight: 2, opacity: 0.6 }
    }
    return { color: '#cbd5f5', weight: 1, opacity: 0.35 }
  },
  pointToLayer: (feature, latlng) => {
    const featureType = ((feature?.properties ?? {}) as Record<string, unknown>).feature_type
    const color = featureType === 'facility' ? '#0ea5e9' : '#6366f1'
    return circleMarker(latlng, {
      radius: featureType === 'facility' ? 5 : 4,
      color,
      weight: 1,
      fillColor: color,
      fillOpacity: 0.85,
      opacity: 0.9,
    })
  },
}

const placeholderType = computed(() => {
  if (props.loading) return 'loading'
  if (!props.tile) return 'no-tile'
  if (!hasRoute.value && !hasFacilities.value) return 'no-route'
  return 'none'
})

const placeholderContent = computed(() => {
  switch (placeholderType.value) {
    case 'loading':
      return {
        title: '地图数据加载中',
        copy: '正在获取基础路径与设施，请稍候…',
      }
    case 'no-tile':
      return {
        title: '暂无基础地图',
        copy: '当前区域缺失 GeoJSON 切片，请检查数据生成流程。',
      }
    case 'no-route':
      return {
        title: '等待路线数据',
        copy: '填写参数并点击「计算路线」，即可在地图上查看路径。',
      }
    default:
      return null
  }
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

        <LGeoJson
          v-if="filteredTile"
          :key="tileSignature"
          :geojson="filteredTile"
          :options="geoJsonOptions"
        />

        <LPolyline
          v-for="segment in segmentPolylines"
          :key="segment.key"
          :lat-lngs="segment.coords"
          :color="segment.color"
          :weight="segment.weight"
          :opacity="0.95"
          line-cap="round"
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

        <LCircleMarker
          v-for="facility in facilityPoints"
          :key="`facility-${facility.id}`"
          :lat-lng="facility.coords"
          :radius="7"
          color="#0f766e"
          fill-color="#14b8a6"
          :fill-opacity="0.92"
          :weight="2"
        >
          <LTooltip>
            <div class="tooltip">
              <span class="order facility">设施</span>
              <span>{{ facility.label }}</span>
              <span class="meta">直线 {{ facility.distance.toFixed(0) }}m · 预计 {{ facility.travelTime.toFixed(1) }}min</span>
            </div>
          </LTooltip>
        </LCircleMarker>
      </LMap>

      <transition name="placeholder-fade">
        <div v-if="placeholderContent" class="map-placeholder">
          <span class="placeholder-title">{{ placeholderContent.title }}</span>
          <span class="placeholder-copy">{{ placeholderContent.copy }}</span>
        </div>
      </transition>
    </div>
    <div v-if="hasRoute || hasFacilities" class="map-legend">
      <span v-if="hasRoute" class="legend-item legend-start">起点</span>
      <span v-if="hasRoute" class="legend-item legend-end">终点</span>
      <template v-if="legendModes.length">
        <span
          v-for="legend in legendModes"
          :key="legend.mode"
          class="legend-item legend-mode"
          :style="{ '--legend-color': legend.color }"
        >
          {{ legend.label }}
        </span>
      </template>
      <span v-if="hasFacilities" class="legend-item legend-facility">设施</span>
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

.placeholder-fade-enter-active,
.placeholder-fade-leave-active {
  transition: opacity 0.3s ease;
}

.placeholder-fade-enter-from,
.placeholder-fade-leave-to {
  opacity: 0;
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
  background-color: var(--legend-color, currentColor);
}

.legend-start {
  color: #22c55e;
}

.legend-end {
  color: #ef4444;
}

.legend-mode {
  color: var(--legend-color, #2563eb);
}

.legend-mode::before {
  width: 18px;
  height: 4px;
  border-radius: 9999px;
}

.legend-facility {
  color: #14b8a6;
}

.legend-facility::before {
  width: 10px;
  height: 10px;
  border-radius: 9999px;
  background-color: currentColor;
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

.order.facility {
  color: #0f766e;
}

.meta {
  font-size: 0.7rem;
  color: #cbd5f5;
}
</style>

import type { FacilityCategory, TransportMode } from '../types/api'

export const INTEREST_SUGGESTIONS: string[] = [
  '自然风光',
  '历史文化',
  '亲子游',
  '探险旅行',
  '美食特色',
  '夜生活',
  '艺术展览',
]

export const SAMPLE_REGION_OPTIONS = [
  { id: 1, name: '重庆景区-001', city: '北京', type: 'scenic' },
  { id: 2, name: '太原大学-002', city: '上海', type: 'campus' },
  { id: 5, name: '蚌埠景区-005', city: '西安', type: 'scenic' },
  { id: 12, name: '广州大学-012', city: '广州', type: 'campus' },
]

export const SAMPLE_ROUTING_COMBINATIONS = [
  {
    label: '西湖景区：节点 1 → 25',
    regionId: 1,
    startNodeId: 1,
    endNodeId: 25,
  },
  {
    label: '西湖景区：节点 3 → 50',
    regionId: 1,
    startNodeId: 3,
    endNodeId: 50,
  },
  {
    label: '清华大学：节点 961 → 980',
    regionId: 2,
    startNodeId: 961,
    endNodeId: 980,
  },
]

export const SAMPLE_FACILITY_QUERIES = [
  {
    label: '西湖景区 · 起点 1 · 半径 600m',
    regionId: 1,
    originNodeId: 1,
    radius: 600,
  },
  {
    label: '清华大学 · 起点 961 · 半径 400m',
    regionId: 2,
    originNodeId: 961,
    radius: 400,
  },
]

export const FACILITY_CATEGORY_LABELS: Record<FacilityCategory, string> = {
  restroom: '卫生间',
  restaurant: '餐厅',
  shop: '商店',
  supermarket: '超市',
  cafe: '咖啡厅',
  atm: 'ATM',
  medical: '医疗点',
  parking: '停车场',
  information: '服务台',
  service: '其他服务',
}

export const TRANSPORT_MODE_LABELS: Record<TransportMode, string> = {
  walk: '步行',
  bike: '骑行',
  electric_cart: '电瓶车',
}

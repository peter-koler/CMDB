import {
  ApiOutlined,
  AppstoreOutlined,
  CloudServerOutlined,
  ClusterOutlined,
  ConsoleSqlOutlined,
  ContainerOutlined,
  DatabaseOutlined,
  DesktopOutlined,
  DeploymentUnitOutlined,
  GatewayOutlined,
  GlobalOutlined,
  HddOutlined,
  LaptopOutlined,
  NodeIndexOutlined,
  SecurityScanOutlined,
  SwitcherOutlined,
  ThunderboltOutlined,
  WindowsOutlined
} from '@ant-design/icons-vue'

export interface ModelIconOption {
  key: string
  label: string
}

const svgToDataUrl = (svg: string) => {
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`
}

const createBadgeSvg = (bg: string, fg: string, label: string, subLabel = '', accent = '') => {
  const accentMarkup = accent
    ? `<circle cx="52" cy="14" r="6" fill="${accent}" fill-opacity="0.92" />`
    : ''
  const subLabelMarkup = subLabel
    ? `<text x="32" y="46" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="11" font-weight="700" fill="${fg}" opacity="0.88">${subLabel}</text>`
    : ''
  return svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="${bg}" />
      <rect x="10" y="10" width="44" height="44" rx="12" fill="rgba(255,255,255,0.12)" />
      ${accentMarkup}
      <text x="32" y="${subLabel ? '31' : '36'}" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="${label.length >= 3 ? '18' : '22'}" font-weight="800" fill="${fg}" letter-spacing="0.6">${label}</text>
      ${subLabelMarkup}
    </svg>`
  )
}

const createWindowsSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#0A66DA" />
      <rect x="14" y="14" width="15" height="15" fill="#ffffff" />
      <rect x="33" y="14" width="17" height="15" fill="#ffffff" opacity="0.96" />
      <rect x="14" y="33" width="15" height="17" fill="#ffffff" opacity="0.96" />
      <rect x="33" y="33" width="17" height="17" fill="#ffffff" />
    </svg>`
  )

const createServerSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#1D4ED8" />
      <rect x="15" y="15" width="34" height="12" rx="4" fill="#F8FAFC" />
      <rect x="15" y="29" width="34" height="12" rx="4" fill="#DBEAFE" />
      <rect x="15" y="43" width="34" height="6" rx="3" fill="#93C5FD" />
      <circle cx="20" cy="21" r="2" fill="#1D4ED8" />
      <circle cx="20" cy="35" r="2" fill="#1D4ED8" />
      <circle cx="44" cy="21" r="2" fill="#22C55E" />
      <circle cx="44" cy="35" r="2" fill="#22C55E" />
    </svg>`
  )

const createCabinetSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#334155" />
      <rect x="21" y="11" width="22" height="42" rx="5" fill="#E2E8F0" />
      <rect x="24" y="16" width="16" height="8" rx="2" fill="#64748B" />
      <rect x="24" y="28" width="16" height="8" rx="2" fill="#64748B" />
      <rect x="24" y="40" width="16" height="8" rx="2" fill="#64748B" />
      <circle cx="38" cy="20" r="1.5" fill="#22C55E" />
      <circle cx="38" cy="32" r="1.5" fill="#22C55E" />
      <circle cx="38" cy="44" r="1.5" fill="#22C55E" />
    </svg>`
  )

const createDatacenterSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#0F766E" />
      <rect x="12" y="18" width="10" height="28" rx="3" fill="#CCFBF1" />
      <rect x="27" y="14" width="10" height="32" rx="3" fill="#E6FFFB" />
      <rect x="42" y="22" width="10" height="24" rx="3" fill="#99F6E4" />
      <path d="M17 18v-5h30v5" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" />
      <path d="M17 46v5h30v-5" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" />
    </svg>`
  )

const createSwitchSvg = (brand: string, bg: string, fg = '#FFFFFF') =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="${bg}" />
      <rect x="12" y="18" width="40" height="16" rx="5" fill="rgba(255,255,255,0.18)" />
      <rect x="12" y="36" width="40" height="10" rx="4" fill="rgba(255,255,255,0.12)" />
      <circle cx="18" cy="26" r="2" fill="${fg}" />
      <circle cx="25" cy="26" r="2" fill="${fg}" />
      <circle cx="32" cy="26" r="2" fill="${fg}" />
      <circle cx="39" cy="26" r="2" fill="${fg}" />
      <circle cx="46" cy="26" r="2" fill="${fg}" />
      <text x="32" y="44" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="${brand.length > 2 ? '9' : '11'}" font-weight="800" fill="${fg}">${brand}</text>
    </svg>`
  )

const createRouterSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#F59E0B" />
      <rect x="14" y="34" width="36" height="10" rx="5" fill="#FFF7ED" />
      <path d="M23 33c0-5 4-9 9-9s9 4 9 9" fill="none" stroke="#FFF7ED" stroke-width="3" stroke-linecap="round" />
      <path d="M27 30c0-3 2-5 5-5s5 2 5 5" fill="none" stroke="#FDBA74" stroke-width="3" stroke-linecap="round" />
      <circle cx="32" cy="29" r="2" fill="#FFF7ED" />
    </svg>`
  )

const createFirewallSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#DC2626" />
      <path d="M32 14l16 6v11c0 10-6.8 18.3-16 21-9.2-2.7-16-11-16-21V20l16-6z" fill="#FEE2E2" />
      <path d="M32 20v22" stroke="#DC2626" stroke-width="3" stroke-linecap="round" />
      <path d="M22 28h20M24 36h16" stroke="#DC2626" stroke-width="3" stroke-linecap="round" />
    </svg>`
  )

const createUpsSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#7C3AED" />
      <rect x="18" y="18" width="28" height="28" rx="8" fill="#F5F3FF" />
      <path d="M34 20L26 33h6l-2 11 8-13h-6l2-11z" fill="#7C3AED" />
    </svg>`
  )

const createNginxSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#009639" />
      <path d="M32 11l18 10.5v21L32 53 14 42.5v-21L32 11z" fill="#ffffff" opacity="0.96" />
      <path d="M25 23.5v16h3.5V29.3l8.7 10.2H39V23.5h-3.5v10l-8.5-10z" fill="#009639" />
    </svg>`
  )

const createDockerSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#0B77D5" />
      <rect x="17" y="29" width="7" height="7" rx="1.4" fill="#ffffff" />
      <rect x="25" y="29" width="7" height="7" rx="1.4" fill="#ffffff" />
      <rect x="33" y="29" width="7" height="7" rx="1.4" fill="#ffffff" />
      <rect x="25" y="21" width="7" height="7" rx="1.4" fill="#ffffff" opacity="0.95" />
      <rect x="33" y="21" width="7" height="7" rx="1.4" fill="#ffffff" opacity="0.95" />
      <path d="M17 38h24c3.8 0 7.1-1.5 9.4-4.5 1.4-.1 2.4-.7 3.6-1.7-1.1-.6-1.8-.8-3-.9.2-1.7-.2-3.2-1.2-4.8-1.3 1.2-1.9 2.4-2.1 4-1.1.4-2 .8-2.8 1.5-.8-.6-1.8-.8-2.9-.8H17z" fill="#ffffff" />
      <circle cx="24" cy="41.5" r="1.1" fill="#0B77D5" />
      <circle cx="29" cy="41.5" r="1.1" fill="#0B77D5" />
      <circle cx="34" cy="41.5" r="1.1" fill="#0B77D5" />
    </svg>`
  )

const createLinuxSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#111827" />
      <ellipse cx="32" cy="28" rx="11" ry="13" fill="#ffffff" />
      <ellipse cx="28" cy="26" rx="1.7" ry="2.2" fill="#111827" />
      <ellipse cx="36" cy="26" rx="1.7" ry="2.2" fill="#111827" />
      <path d="M29 32c1.7 1.1 4.3 1.1 6 0" fill="none" stroke="#F59E0B" stroke-width="2.5" stroke-linecap="round" />
      <path d="M26 16l-4 6M38 16l4 6" stroke="#111827" stroke-width="3" stroke-linecap="round" />
      <ellipse cx="32" cy="45" rx="12" ry="6.5" fill="#F59E0B" />
      <path d="M25 43l-4 7M39 43l4 7" stroke="#F59E0B" stroke-width="3" stroke-linecap="round" />
    </svg>`
  )

const createMysqlSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#0F4C81" />
      <path d="M17 39c3-9 8.8-15.1 16.3-16.6 6.6-1.3 11.7 1.2 14.7 5.7-2.9-.8-5.5-.3-8.4 1.5 1.5.3 2.7.9 3.8 1.9-3.5.2-6.3 1.5-8.5 3.8 1.8-.2 3.4.2 4.8 1.2-4 1.1-7.1 3.6-9.8 7.5-2.2-.6-3.8-1.6-5.2-3.5-1.5 1.2-2.8 1.7-4.8 1.9.7-1.2 1-2.1 1-3.4-1 .3-1.9.3-4-.1z" fill="#ffffff" />
      <circle cx="42" cy="22" r="2" fill="#F59E0B" />
    </svg>`
  )

const createPostgresSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#336791" />
      <path d="M23 25c0-5.6 4.5-10 9-10 4.8 0 9 4.4 9 10v13.5c0 5.2-4.1 10.5-9 10.5-4.7 0-9-5-9-10.5z" fill="#ffffff" />
      <circle cx="28" cy="26" r="1.6" fill="#336791" />
      <circle cx="36" cy="26" r="1.6" fill="#336791" />
      <path d="M40 22c3.3-.2 5.4.9 6.7 3.1 1.6 2.6 1.6 6.2.1 8.8-1.1 2-3.2 3.1-5.7 3.4" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" />
      <path d="M29 33c2 1.1 4 1.1 6 0" fill="none" stroke="#60A5FA" stroke-width="2.3" stroke-linecap="round" />
      <path d="M27 47c2.8 1 5.6 1 8.4 0" fill="none" stroke="#DBEAFE" stroke-width="2.3" stroke-linecap="round" />
    </svg>`
  )

const createOracleSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#C74634" />
      <ellipse cx="32" cy="32" rx="17" ry="10" fill="none" stroke="#ffffff" stroke-width="6" />
      <ellipse cx="32" cy="32" rx="10" ry="4.5" fill="none" stroke="#FECACA" stroke-width="2" opacity="0.9" />
    </svg>`
  )

const createTomcatSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#B45309" />
      <circle cx="32" cy="32" r="15" fill="#FCD34D" />
      <circle cx="32" cy="32" r="10" fill="none" stroke="#92400E" stroke-width="3" stroke-dasharray="5 4" />
      <path d="M32 18v6M32 40v6M18 32h6M40 32h6M22.5 22.5l4.2 4.2M37.3 37.3l4.2 4.2M41.5 22.5l-4.2 4.2M26.7 37.3l-4.2 4.2" stroke="#92400E" stroke-width="2.5" stroke-linecap="round" />
    </svg>`
  )

const createHuaweiSwitchSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#CF1322" />
      <path d="M32 15l3.5 9.2 8.6-4.4-4.8 8.4 9.5.8-8.3 4.6 6.1 7.2-9.4-1.6.8 9.4-5.9-7.4-5.9 7.4.8-9.4-9.4 1.6 6.1-7.2-8.3-4.6 9.5-.8-4.8-8.4 8.6 4.4z" fill="#ffffff" />
      <rect x="18" y="46" width="28" height="4" rx="2" fill="#FCA5A5" />
    </svg>`
  )

const createCiscoSwitchSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#0284C7" />
      <rect x="18" y="39" width="28" height="8" rx="4" fill="#E0F2FE" />
      <rect x="20" y="18" width="2.5" height="11" rx="1.2" fill="#E0F2FE" />
      <rect x="26" y="14" width="2.5" height="15" rx="1.2" fill="#E0F2FE" />
      <rect x="31" y="11" width="2.5" height="18" rx="1.2" fill="#ffffff" />
      <rect x="36" y="14" width="2.5" height="15" rx="1.2" fill="#E0F2FE" />
      <rect x="42" y="18" width="2.5" height="11" rx="1.2" fill="#E0F2FE" />
      <circle cx="25" cy="43" r="1" fill="#0284C7" />
      <circle cx="32" cy="43" r="1" fill="#0284C7" />
      <circle cx="39" cy="43" r="1" fill="#0284C7" />
    </svg>`
  )

const createTplinkSwitchSvg = () =>
  svgToDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
      <rect x="4" y="4" width="56" height="56" rx="16" fill="#0F766E" />
      <path d="M20 21h24v5H34v17h-6V26H20z" fill="#ffffff" />
      <path d="M36 34h8c0 5.5-4.2 9-9.8 9-4 0-7.5-1.8-9.1-5l5-2.4c.8 1.3 2.1 2 4 2 1.2 0 2-.3 2.8-1.2H36z" fill="#CCFBF1" />
    </svg>`
  )

const createAssetMap = () => ({
  NginxOutlined: createNginxSvg(),
  SwitchOutlined: createSwitchSvg('SW', '#2563EB'),
  RouterOutlined: createRouterSvg(),
  FirewallOutlined: createFirewallSvg(),
  DockerOutlined: createDockerSvg(),
  UpsOutlined: createUpsSvg(),
  CabinetOutlined: createCabinetSvg(),
  DatacenterOutlined: createDatacenterSvg(),
  LinuxOutlined: createLinuxSvg(),
  WindowsOutlined: createWindowsSvg(),
  ServerOutlined: createServerSvg(),
  RedisOutlined: createBadgeSvg('#D82C20', '#FFFFFF', 'RD', 'redis', '#FCA5A5'),
  MemcacheOutlined: createBadgeSvg('#6D28D9', '#FFFFFF', 'MC', 'cache', '#C4B5FD'),
  MySqlOutlined: createMysqlSvg(),
  PostgreSqlOutlined: createPostgresSvg(),
  OracleOutlined: createOracleSvg(),
  DmOutlined: createBadgeSvg('#5B21B6', '#FFFFFF', 'DM', 'db', '#C4B5FD'),
  OceanBaseOutlined: createBadgeSvg('#16A34A', '#FFFFFF', 'OB', 'db', '#86EFAC'),
  OpenGaussOutlined: createBadgeSvg('#0F766E', '#FFFFFF', 'OG', 'db', '#5EEAD4'),
  SqlServerOutlined: createBadgeSvg('#A61E4D', '#FFFFFF', 'MS', 'sql', '#FDA4AF'),
  TomcatOutlined: createTomcatSvg(),
  HuaweiSwitchOutlined: createHuaweiSwitchSvg(),
  H3cSwitchOutlined: createSwitchSvg('H3C', '#E11D48'),
  CiscoSwitchOutlined: createCiscoSwitchSvg(),
  TplinkSwitchOutlined: createTplinkSwitchSvg(),
  NetworkOutlined: createBadgeSvg('#1D4ED8', '#FFFFFF', 'NET', '', '#93C5FD')
})

const modelIconAssetUrlMap: Record<string, string> = createAssetMap()

export const modelIconComponentMap: Record<string, any> = {
  AppstoreOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  ClusterOutlined,
  HddOutlined,
  ApiOutlined,
  DeploymentUnitOutlined,
  ContainerOutlined,
  LaptopOutlined,
  GlobalOutlined,
  NginxOutlined: DeploymentUnitOutlined,
  SwitchOutlined: SwitcherOutlined,
  RouterOutlined: GatewayOutlined,
  FirewallOutlined: SecurityScanOutlined,
  DockerOutlined: ContainerOutlined,
  UpsOutlined: ThunderboltOutlined,
  CabinetOutlined: HddOutlined,
  DatacenterOutlined: ClusterOutlined,
  LinuxOutlined: DesktopOutlined,
  WindowsOutlined,
  ServerOutlined: CloudServerOutlined,
  RedisOutlined: ClusterOutlined,
  MemcacheOutlined: DatabaseOutlined,
  MySqlOutlined: ConsoleSqlOutlined,
  PostgreSqlOutlined: ConsoleSqlOutlined,
  OracleOutlined: ConsoleSqlOutlined,
  DmOutlined: DatabaseOutlined,
  OceanBaseOutlined: DatabaseOutlined,
  OpenGaussOutlined: DatabaseOutlined,
  SqlServerOutlined: ConsoleSqlOutlined,
  TomcatOutlined: DeploymentUnitOutlined,
  HuaweiSwitchOutlined: SwitcherOutlined,
  H3cSwitchOutlined: SwitcherOutlined,
  CiscoSwitchOutlined: SwitcherOutlined,
  TplinkSwitchOutlined: SwitcherOutlined,
  NetworkOutlined: NodeIndexOutlined
}

export const modelBuiltinIconOptions: ModelIconOption[] = [
  { key: 'AppstoreOutlined', label: '应用' },
  { key: 'DatabaseOutlined', label: '通用数据库' },
  { key: 'CloudServerOutlined', label: '云服务器' },
  { key: 'ClusterOutlined', label: '集群' },
  { key: 'HddOutlined', label: '存储' },
  { key: 'ApiOutlined', label: '接口服务' },
  { key: 'DeploymentUnitOutlined', label: '部署单元' },
  { key: 'ContainerOutlined', label: '容器' },
  { key: 'LaptopOutlined', label: '终端设备' },
  { key: 'GlobalOutlined', label: '网络' },
  { key: 'NginxOutlined', label: 'Nginx' },
  { key: 'SwitchOutlined', label: '交换机' },
  { key: 'RouterOutlined', label: '路由器' },
  { key: 'FirewallOutlined', label: '防火墙' },
  { key: 'DockerOutlined', label: 'Docker' },
  { key: 'UpsOutlined', label: 'UPS' },
  { key: 'CabinetOutlined', label: '机柜' },
  { key: 'DatacenterOutlined', label: '机房' },
  { key: 'LinuxOutlined', label: 'Linux' },
  { key: 'WindowsOutlined', label: 'Windows' },
  { key: 'ServerOutlined', label: '服务器' },
  { key: 'RedisOutlined', label: 'Redis' },
  { key: 'MemcacheOutlined', label: 'Memcache' },
  { key: 'MySqlOutlined', label: 'MySQL' },
  { key: 'PostgreSqlOutlined', label: 'PostgreSQL' },
  { key: 'OracleOutlined', label: 'Oracle' },
  { key: 'DmOutlined', label: '达梦数据库' },
  { key: 'OceanBaseOutlined', label: 'OceanBase 数据库' },
  { key: 'OpenGaussOutlined', label: 'openGauss 数据库' },
  { key: 'SqlServerOutlined', label: 'SQL Server 数据库' },
  { key: 'TomcatOutlined', label: 'Tomcat' },
  { key: 'HuaweiSwitchOutlined', label: '华为交换机' },
  { key: 'H3cSwitchOutlined', label: '华三交换机' },
  { key: 'CiscoSwitchOutlined', label: '思科交换机' },
  { key: 'TplinkSwitchOutlined', label: 'TP-Link 交换机' }
]

const modelIconLabelMap = modelBuiltinIconOptions.reduce<Record<string, string>>((acc, item) => {
  acc[item.key] = item.label
  return acc
}, {})

export const getModelIconComponent = (iconName?: string) => {
  return modelIconComponentMap[iconName || ''] || AppstoreOutlined
}

export const getModelIconAssetUrl = (iconName?: string) => {
  return modelIconAssetUrlMap[iconName || ''] || ''
}

export const getModelIconLabel = (iconName?: string) => {
  return modelIconLabelMap[iconName || ''] || '应用'
}

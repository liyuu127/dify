'use client'
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { useTranslation } from 'react-i18next'
import {
  RiEqualizer2Line,
  RiExternalLinkLine,
  RiPaintBrushLine,
  RiWindowLine,
} from '@remixicon/react'
import type { ConfigParams } from './settings'
import AppBasic from '@/app/components/app-sidebar/basic'
import { asyncRunSafe } from '@/utils'
import { basePath } from '@/utils/var'
import { useStore as useAppStore } from '@/app/components/app/store'
import type { AppDetailResponse } from '@/models/app'
import { useAppContext } from '@/context/app-context'
import type { AppSSO } from '@/types/app'
import { fetchAppDetail } from '@/service/apps'
import { AccessMode } from '@/models/access-control'
import { useAppWhiteListSubjects } from '@/service/access-control'
import { useGlobalPublicStore } from '@/context/global-public-context'

export type IAppCardProps = {
  className?: string
  appInfo: AppDetailResponse & Partial<AppSSO>
  isInPanel?: boolean
  cardType?: 'api' | 'webapp' | 'app' | 'dataset' | 'notion' | 'PermissionSvg'
  customBgColor?: string
  onChangeStatus: (val: boolean) => Promise<void>
  onSaveSiteConfig?: (params: ConfigParams) => Promise<void>
  onGenerateCode?: () => Promise<void>
}

function AppPermission({
  appInfo,
  isInPanel,
  cardType = 'webapp',
  customBgColor,
  onChangeStatus,
  onSaveSiteConfig,
  onGenerateCode,
  className,
}: IAppCardProps) {
  const router = useRouter()
  const pathname = usePathname()
  const { isCurrentWorkspaceManager, isCurrentWorkspaceEditor } = useAppContext()
  const appDetail = useAppStore(state => state.appDetail)
  const setAppDetail = useAppStore(state => state.setAppDetail)
  const [showSettingsModal, setShowSettingsModal] = useState(false)
  const [showEmbedded, setShowEmbedded] = useState(false)
  const [showCustomizeModal, setShowCustomizeModal] = useState(false)
  const [genLoading, setGenLoading] = useState(false)
  const [showConfirmDelete, setShowConfirmDelete] = useState(false)
  const [showAccessControl, setShowAccessControl] = useState<boolean>(false)
  const { t } = useTranslation()
  const systemFeatures = useGlobalPublicStore(s => s.systemFeatures)
  const { data: appAccessSubjects } = useAppWhiteListSubjects(appDetail?.id, systemFeatures.webapp_auth.enabled && appDetail?.access_mode === AccessMode.SPECIFIC_GROUPS_MEMBERS)

  const OPERATIONS_MAP = useMemo(() => {
    const operationsMap = {
      webapp: [
        {
 opName: t('appOverview.overview.appInfo.launch'),
opIcon: RiExternalLinkLine,
},
      ] as {
 opName: string;
opIcon: any
}[],
      // 注释掉API访问，因为不需要
      // api: [{ opName: t('appOverview.overview.apiInfo.doc'), opIcon: RiBookOpenLine }],
      api: [],
      app: [],
    }
    if (appInfo.mode !== 'completion' && appInfo.mode !== 'workflow') {
 operationsMap.webapp.push({
 opName: t('appOverview.overview.appInfo.embedded.entry'),
opIcon: RiWindowLine,
})
}

    operationsMap.webapp.push({
 opName: t('appOverview.overview.appInfo.customize.entry'),
opIcon: RiPaintBrushLine,
})

    if (isCurrentWorkspaceEditor) {
 operationsMap.webapp.push({
 opName: t('appOverview.overview.appInfo.settings.entry'),
opIcon: RiEqualizer2Line,
})
}

    return operationsMap
  }, [isCurrentWorkspaceEditor, appInfo, t])

  const isApp = cardType === 'webapp'
  const basicName = t('appOverview.overview.permission.title')
  const toggleDisabled = isApp ? !isCurrentWorkspaceEditor : !isCurrentWorkspaceManager
  const runningStatus = isApp ? appInfo.enable_site : appInfo.enable_api
  const { app_base_url, access_token } = appInfo.site ?? {}
  const appMode = (appInfo.mode !== 'completion' && appInfo.mode !== 'workflow') ? 'chat' : appInfo.mode
  const appUrl = `${app_base_url}${basePath}/${appMode}/${access_token}`
  const apiUrl = appInfo?.api_base_url

  const genClickFuncByName = (opName: string) => {
    switch (opName) {
      case t('appOverview.overview.appInfo.launch'):
        return () => {
          window.open(appUrl, '_blank')
        }
      case t('appOverview.overview.appInfo.customize.entry'):
        return () => {
          setShowCustomizeModal(true)
        }
      case t('appOverview.overview.appInfo.settings.entry'):
        return () => {
          setShowSettingsModal(true)
        }
      case t('appOverview.overview.appInfo.embedded.entry'):
        return () => {
          setShowEmbedded(true)
        }
      default:
        // jump to page develop
        return () => {
          const pathSegments = pathname.split('/')
          pathSegments.pop()
          router.push(`${pathSegments.join('/')}/develop`)
        }
    }
  }

  const onGenCode = async () => {
    if (onGenerateCode) {
      setGenLoading(true)
      await asyncRunSafe(onGenerateCode())
      setGenLoading(false)
    }
  }

  const [isAppAccessSet, setIsAppAccessSet] = useState(true)
  useEffect(() => {
    if (appDetail && appAccessSubjects) {
      if (appDetail.access_mode === AccessMode.SPECIFIC_GROUPS_MEMBERS && appAccessSubjects.groups?.length === 0 && appAccessSubjects.members?.length === 0)
        setIsAppAccessSet(false)
      else
        setIsAppAccessSet(true)
    }
    else {
      setIsAppAccessSet(true)
    }
  }, [appAccessSubjects, appDetail])

  const handleClickAccessControl = useCallback(() => {
    if (!appDetail)
      return
    setShowAccessControl(true)
  }, [appDetail])
  const handleAccessControlUpdate = useCallback(() => {
    fetchAppDetail({
 url: '/apps',
id: appDetail!.id,
}).then((res) => {
      setAppDetail(res)
      setShowAccessControl(false)
    })
  }, [appDetail, setAppDetail])

  return (
    <div
      className={
        `${isInPanel ? 'border-l-[0.5px] border-t' : 'border-[0.5px] shadow-xs'} w-full max-w-full rounded-xl border-effects-highlight ${className ?? ''}`}
    >
      <div className={`${customBgColor ?? 'bg-background-default'} rounded-xl`}>
        <div className='flex w-full flex-col items-start justify-center gap-3 self-stretch border-b-[0.5px] border-divider-subtle p-3'>
          <div className='flex w-full items-center gap-3 self-stretch'>
            <AppBasic
              iconType={cardType}
              icon={appInfo.icon}
              icon_background={appInfo.icon_background}
              name={basicName}
              type={
                t('appOverview.overview.permission.explanation')
              }
            />
            {/* <div className='flex shrink-0 items-center gap-1'>
              <Indicator color={runningStatus ? 'green' : 'yellow'} />
              <div className={`${runningStatus ? 'text-text-success' : 'text-text-warning'} system-xs-semibold-uppercase`}>
                {runningStatus
                  ? t('appOverview.overview.status.running')
                  : t('appOverview.overview.status.disable')}
              </div>
            </div> */}
            {/* <Switch defaultValue={runningStatus} onChange={onChangeStatus} disabled={toggleDisabled} /> */}
          </div>
        </div>
      </div>
    </div>
  )
}

export default AppPermission

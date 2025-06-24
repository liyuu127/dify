'use client'
import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  RiEqualizer2Line,
  RiExternalLinkLine,
  RiPaintBrushLine,
  RiWindowLine,
} from '@remixicon/react'
import type { ConfigParams } from './settings'
import AppBasic from '@/app/components/app-sidebar/basic'
import { useStore as useAppStore } from '@/app/components/app/store'
import type { AppDetailResponse } from '@/models/app'
import { useAppContext } from '@/context/app-context'
import type { AppSSO } from '@/types/app'
import { updateAppInfo } from '@/service/apps'
import { AccessMode } from '@/models/access-control'
import { useAppWhiteListSubjects } from '@/service/access-control'
import { useGlobalPublicStore } from '@/context/global-public-context'
import DatasetDetailContext from '@/context/dataset-detail'
import { useContext } from 'use-context-selector'
import type { Member } from '@/models/common'
import { fetchMembers } from '@/service/common'
import { useMount } from 'ahooks'
import Button from '@/app/components/base/button'
import { DatasetPermission } from '@/models/datasets'
// 引入组件
import PermissionSelector from '@/app/components/datasets/settings/permission-selector'

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
  // const router = useRouter()
  // const pathname = usePathname()
  const { isCurrentWorkspaceManager, isCurrentWorkspaceEditor } = useAppContext()
  const appDetail = useAppStore(state => state.appDetail)
  const setAppDetail = useAppStore(state => state.setAppDetail)
  // const [showSettingsModal, setShowSettingsModal] = useState(false)
  // const [showEmbedded, setShowEmbedded] = useState(false)
  // const [showCustomizeModal, setShowCustomizeModal] = useState(false)
  // const [genLoading, setGenLoading] = useState(false)
  // const [showConfirmDelete, setShowConfirmDelete] = useState(false)
  // const [showAccessControl, setShowAccessControl] = useState<boolean>(false)
  const { dataset: currentDataset, mutateDatasetRes: mutateDatasets } = useContext(DatasetDetailContext)
  const [selectedMemberIDs, setSelectedMemberIDs] = useState<string[]>(currentDataset?.partial_member_list || [])
  const { t } = useTranslation()
  const systemFeatures = useGlobalPublicStore(s => s.systemFeatures)
  const { data: appAccessSubjects } = useAppWhiteListSubjects(appDetail?.id, systemFeatures.webapp_auth.enabled && appDetail?.access_mode === AccessMode.SPECIFIC_GROUPS_MEMBERS)
  // const { isCurrentWorkspaceDatasetOperator } = useAppContext()
  const [permission, setPermission] = useState(currentDataset?.permission || DatasetPermission.onlyMe)
  const [memberList, setMemberList] = useState<Member[]>([])
  const getMembers = async () => {
    const { accounts } = await fetchMembers({
      url: '/workspaces/current/members',
      params: {},
    })
    if (!accounts)
      setMemberList([])
    else
      setMemberList(accounts)
  }
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
  useMount(() => {
    getMembers()
  })

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
  // 保存权限
  const handleSave = async () => {
    console.log(selectedMemberIDs, permission, appInfo, '=======================')
    const res = await updateAppInfo({
        appID: appInfo.id,
        name: appInfo.name,
        icon_type: appInfo.icon_type,
        icon: appInfo.icon,
        description: appInfo.description,
        use_icon_as_answer_icon: appInfo.use_icon_as_answer_icon,
      })
      console.log(res, '----------------------')
  }
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
            <div>
              <Button
                className='min-w-12'
                variant='primary'
                onClick={handleSave}
              >
                {t('datasetSettings.form.save')}
              </Button>
            </div>
          </div>
          <div style={{ width: '100%' }}>
            <PermissionSelector
              permission={permission}
              value={selectedMemberIDs}
              onChange={v => setPermission(v)}
              onMemberSelect={setSelectedMemberIDs}
              memberList={memberList}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default AppPermission

'use client'
import { useCallback, useEffect } from 'react'
import { useBoolean } from 'ahooks'
import { useSelectedLayoutSegment } from 'next/navigation'
import AppNav from './app-nav'
import DatasetNav from './dataset-nav'
import { useAppContext } from '@/context/app-context'
import useBreakpoints, { MediaType } from '@/hooks/use-breakpoints'
import { useProviderContext } from '@/context/provider-context'
import { useModalContext } from '@/context/modal-context'
import { Plan } from '../billing/type'

const navClassName = `
  flex items-center relative mr-0 sm:mr-3 px-3 h-8 rounded-xl
  font-medium text-sm
  cursor-pointer
`

const Header = () => {
  const { isCurrentWorkspaceEditor, isCurrentWorkspaceDatasetOperator } = useAppContext()
  const selectedSegment = useSelectedLayoutSegment()
  const media = useBreakpoints()
  const isMobile = media === MediaType.mobile
  const [isShowNavMenu, { toggle, setFalse: hideNavMenu }] = useBoolean(false)
  const { enableBilling, plan } = useProviderContext()
  const { setShowPricingModal, setShowAccountSettingModal } = useModalContext()
  const isFreePlan = plan.type === Plan.sandbox
  const handlePlanClick = useCallback(() => {
    if (isFreePlan)
      setShowPricingModal()
    else
      setShowAccountSettingModal({ payload: 'billing' })
  }, [isFreePlan, setShowAccountSettingModal, setShowPricingModal])

  useEffect(() => {
    hideNavMenu()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSegment])
  return (
    <div style={{ backgroundColor: '#0a2858' }} className='relative flex flex-1 items-center justify-between'>
      {/* 注释掉探索和工具栏，因为这两个功能暂时不需要 */}
      {/* <div className='flex items-center'>
        {isMobile && <div
          className='flex h-8 w-8 cursor-pointer items-center justify-center'
          onClick={toggle}
        >
          <Bars3Icon className="h-4 w-4 text-gray-500" />
        </div>}
        {
          !isMobile
          && <div className='flex shrink-0 items-center gap-1.5 self-stretch pl-3'>
            <Link href="/apps" className='flex h-8 shrink-0 items-center justify-center gap-2 px-0.5'>
              <DifyLogo />
            </Link>
            <div className='font-light text-divider-deep'>/</div>
            <div className='flex items-center gap-0.5'>
              <WorkspaceProvider>
                <WorkplaceSelector />
              </WorkspaceProvider>
              {enableBilling ? <PlanBadge allowHover sandboxAsUpgrade plan={plan.type} onClick={handlePlanClick} /> : <LicenseNav />}
            </div>
          </div>
        }
      </div >
      {isMobile && (
        <div className='flex'>
          <Link href="/apps" className='mr-4 flex items-center'>
            <DifyLogo />
          </Link>
          <div className='font-light text-divider-deep'>/</div>
          {enableBilling ? <PlanBadge allowHover sandboxAsUpgrade plan={plan.type} onClick={handlePlanClick} /> : <LicenseNav />}
        </div >
      )} */}
      {
        !isMobile && (
          <div className='absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 items-center'>
            {/* 注释掉探索和工具栏，因为这两个功能暂时不需要 */}
            {/* {!isCurrentWorkspaceDatasetOperator && <ExploreNav className={navClassName} />} */}
            {!isCurrentWorkspaceDatasetOperator && <AppNav />}
            {(isCurrentWorkspaceEditor || isCurrentWorkspaceDatasetOperator) && <DatasetNav />}
            {/* {!isCurrentWorkspaceDatasetOperator && <ToolsNav className={navClassName} />} */}
          </div>
        )
      }
      {/* 注释掉环境变量和插件，因为这两个功能暂时不需要 */}
      {/* <div className='flex shrink-0 items-center pr-3'>
        <EnvNav />
        <div className='mr-2'>
          <PluginsNav />
        </div>
        <AccountDropdown />
      </div> */}
      {
        (isMobile && isShowNavMenu) && (
          <div className='flex w-full flex-col gap-y-1 p-2'>
            {/* {!isCurrentWorkspaceDatasetOperator && <ExploreNav className={navClassName} />} */}
            {!isCurrentWorkspaceDatasetOperator && <AppNav />}
            {(isCurrentWorkspaceEditor || isCurrentWorkspaceDatasetOperator) && <DatasetNav />}
            {/* {!isCurrentWorkspaceDatasetOperator && <ToolsNav className={navClassName} />} */}
          </div>
        )
      }
    </div >
  )
}
export default Header

'use client'
import React from 'react'
import { useContext } from 'use-context-selector'
import I18n from '@/context/i18n'
import dynamic from 'next/dynamic'

// Avoid rendering the logo and theme selector on the server
const DifyLogo = dynamic(() => import('@/app/components/base/logo/dify-logo'), {
  ssr: false,
  loading: () => <div className='h-7 w-16 bg-transparent' />,
})
const ThemeSelector = dynamic(() => import('@/app/components/base/theme-selector'), {
  ssr: false,
  loading: () => <div className='size-8 bg-transparent' />,
})

const Header = () => {
  const { locale, setLocaleOnClient } = useContext(I18n)

  return (
    <div className='flex w-full items-center justify-between p-6'>
      {/* 注释掉logo */}
      {/* <DifyLogo size='large' /> */}
      <div className='flex items-center gap-1'>
        {/* 注释掉语言选择 */}
        {/* <Select
          value={locale}
          items={languages.filter(item => item.supported)}
          onChange={(value) => {
            setLocaleOnClient(value as Locale)
          }}
        /> */}
        {/* 注释掉分割线 */}
        {/* <Divider type='vertical' className='mx-0 ml-2 h-4' /> */}
        {/* <ThemeSelector /> */}
      </div>
    </div>
  )
}

export default Header

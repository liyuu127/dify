'use client'
import type { FC } from 'react'
import classNames from '@/utils/classnames'
import useTheme from '@/hooks/use-theme'
import { basePath } from '@/utils/var'
import { useGlobalPublicStore } from '@/context/global-public-context'

export type LogoStyle = 'default' | 'monochromeWhite'

export const logoPathMap: Record<LogoStyle, string> = {
  default: '/logo/App-logo.png',
  monochromeWhite: '/logo/App-logo.png',
}

export type LogoSize = 'large' | 'medium' | 'small'

export const logoSizeMap: Record<LogoSize, string> = {
  large: 'w-12 h-12',
  medium: 'w-12 h-[22px]',
  small: 'w-9 h-4',
}

type AppLogoProps = {
  style?: LogoStyle
  size?: LogoSize
  className?: string
}

const AppLogo: FC<AppLogoProps> = ({
  style = 'default',
  size = 'medium',
  className,
}) => {
  const { theme } = useTheme()
  const themedStyle = (theme === 'dark' && style === 'default') ? 'monochromeWhite' : style
  const { systemFeatures } = useGlobalPublicStore()
  const hasBrandingLogo = Boolean(systemFeatures.branding.enabled && systemFeatures.branding.workspace_logo)

  let src = `${basePath}${logoPathMap[themedStyle]}`
  if (hasBrandingLogo)
    src = systemFeatures.branding.workspace_logo

  return (
    <img
      src={src}
      className={classNames('block object-contain', logoSizeMap[size], hasBrandingLogo && 'w-auto', className)}
      alt={hasBrandingLogo ? 'Logo' : 'App logo'}
    />
  )
}

export default AppLogo

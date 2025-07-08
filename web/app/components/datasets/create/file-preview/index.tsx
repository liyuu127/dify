'use client'
import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { XMarkIcon } from '@heroicons/react/20/solid'
import Loading from '@/app/components/base/loading'
import s from './index.module.css'
import cn from '@/utils/classnames'
import type { CustomFile as File } from '@/models/datasets'

// 扩展File类型，添加analysisId属性和resolveMethod标识
type ExtendedFile = File & {
  analysisId?: string
  resolveMethod?: 'fast' | 'multimodal'
}
import { fetchFilePreview } from '@/service/common'

type IProps = {
  file?: ExtendedFile
  hidePreview: () => void
}

const FilePreview = ({
  file,
  hidePreview,
}: IProps) => {
  const { t } = useTranslation()
  const [previewContent, setPreviewContent] = useState('')
  const [loading, setLoading] = useState(true)

  const getPreviewContent = async (fileID: string) => {
    try {
      const res = await fetchFilePreview({ fileID })
      setPreviewContent(res.content)
      setLoading(false)
    }
    catch { }
  }
  const getFileName = (currentFile?: File) => {
    if (!currentFile)
      return ''
    const arr = currentFile.name.split('.')
    return arr.slice(0, -1).join()
  }

  useEffect(() => {
    if (file?.id) {
      setLoading(true)

      // 根据resolveMethod属性决定使用哪个ID
      let previewID = file.id
      // 如果是多模态解析且有analysisId，就使用analysisId
      if ((file as ExtendedFile).resolveMethod === 'multimodal' && (file as ExtendedFile).analysisId) previewID = (file as ExtendedFile).analysisId as string

      getPreviewContent(previewID)
    }
  }, [file])

  return (
    <div className={cn(s.filePreview, 'h-full')}>
      <div className={cn(s.previewHeader)}>
        <div className={cn(s.title, 'title-md-semi-bold')}>
          <span>{t('datasetCreation.stepOne.filePreview')}</span>
          <div className='flex h-6 w-6 cursor-pointer items-center justify-center' onClick={hidePreview}>
            <XMarkIcon className='h-4 w-4'></XMarkIcon>
          </div>
        </div>
        <div className={cn(s.fileName, 'system-xs-medium')}>
          <span>{getFileName(file)}</span><span className={cn(s.filetype)}>.{file?.extension}</span>
        </div>
      </div>
      <div className={cn(s.previewContent)}>
        {loading && <Loading type='area' />}
        {!loading && (
          <div className={cn(s.fileContent, 'body-md-regular')}>{previewContent}</div>
        )}
      </div>
    </div>
  )
}

export default FilePreview

'use client'
import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import AppUnavailable from '../../base/app-unavailable'
import { ModelTypeEnum } from '../../header/account-setting/model-provider-page/declarations'
import type { StepOneRef } from './step-one'
import StepOne from './step-one'
import StepTwo from './step-two'
import StepThree from './step-three'
import { TopBar } from './top-bar'
import { DataSourceType } from '@/models/datasets'
import type { CrawlOptions, CrawlResultItem, DataSet, FileItem, createDocumentResponse } from '@/models/datasets'
import { fetchDataSource } from '@/service/common'
import { fetchDatasetDetail } from '@/service/datasets'
import { DataSourceProvider, type NotionPage } from '@/models/common'
import { useModalContext } from '@/context/modal-context'
import { useDefaultModel } from '@/app/components/header/account-setting/model-provider-page/hooks'

// 扩展FileItem类型，添加解析类型属性
type ExtendedFileItem = FileItem & {
  parseType?: 'fast' | 'multimodal'
}

type DatasetUpdateFormProps = {
  datasetId?: string
}

const DEFAULT_CRAWL_OPTIONS: CrawlOptions = {
  crawl_sub_pages: true,
  only_main_content: true,
  includes: '',
  excludes: '',
  limit: 10,
  max_depth: '',
  use_sitemap: true,
}

const DatasetUpdateForm = ({ datasetId }: DatasetUpdateFormProps) => {
  const { t } = useTranslation()
  const { setShowAccountSettingModal } = useModalContext()
  const [hasConnection, setHasConnection] = useState(true)
  const [dataSourceType, setDataSourceType] = useState<DataSourceType>(DataSourceType.FILE)
  const [step, setStep] = useState(1)
  const [indexingTypeCache, setIndexTypeCache] = useState('')
  const [retrievalMethodCache, setRetrievalMethodCache] = useState('')
  const [fileList, setFiles] = useState<ExtendedFileItem[]>([])
  const [result, setResult] = useState<createDocumentResponse | undefined>()
  const [hasError, setHasError] = useState(false)
  const { data: embeddingsDefaultModel } = useDefaultModel(ModelTypeEnum.textEmbedding)
  const stepOneRef = useRef<StepOneRef>(null)

  const [notionPages, setNotionPages] = useState<NotionPage[]>([])
  const updateNotionPages = (value: NotionPage[]) => {
    setNotionPages(value)
  }

  const [websitePages, setWebsitePages] = useState<CrawlResultItem[]>([])
  const [crawlOptions, setCrawlOptions] = useState<CrawlOptions>(DEFAULT_CRAWL_OPTIONS)

  const updateFileList = (preparedFiles: ExtendedFileItem[]) => {
    setFiles(preparedFiles)
  }
  const [websiteCrawlProvider, setWebsiteCrawlProvider] = useState<DataSourceProvider>(DataSourceProvider.fireCrawl)
  const [websiteCrawlJobId, setWebsiteCrawlJobId] = useState('')

  const updateFile = (fileItem: ExtendedFileItem, progress: number, list: ExtendedFileItem[]) => {
    // 使用函数式更新确保基于最新状态
    setFiles((prevFiles) => {
      // 找到目标文件索引
      const fileIndex = prevFiles.findIndex(file => file.fileID === fileItem.fileID)
      if (fileIndex === -1) return prevFiles // 未找到匹配文件，返回原状态
      // 创建新数组
      const newFiles = [...prevFiles]
      // 更新目标文件的完整信息
      newFiles[fileIndex] = {
        ...fileItem, // 保留完整的fileItem信息
        progress, // 更新进度
      }
      return newFiles
    })
  }

  // 添加处理解析类型变化的专用函数
  const updateFileParseType = (fileID: string, parseType: 'fast' | 'multimodal', updatedFileData?: any) => {
    setFiles((prevFiles) => {
      const fileIndex = prevFiles.findIndex(file => file.fileID === fileID)
      if (fileIndex === -1) return prevFiles
      const newFiles = [...prevFiles]
      newFiles[fileIndex] = {
        ...newFiles[fileIndex],
        parseType,
        file: updatedFileData || newFiles[fileIndex].file,
      }
      return newFiles
    })
  }

  const updateIndexingTypeCache = (type: string) => {
    setIndexTypeCache(type)
  }
  const updateResultCache = (res?: createDocumentResponse) => {
    setResult(res)
  }
  const updateRetrievalMethodCache = (method: string) => {
    setRetrievalMethodCache(method)
  }

  const nextStep = useCallback(() => {
    setStep(step + 1)
  }, [step, setStep])

  const changeStep = useCallback((delta: number) => {
    // 如果是返回上一步，清空文件和缓存
    if (delta < 0) {
      // 调用StepOne组件中的clearFilesAndCache方法
      stepOneRef.current?.clearFilesAndCache()

      // 同时清空fileList状态和其他相关状态
      setFiles([])

      // 如果有其他需要重置的状态，也可以在这里重置
      // 例如：重置indexingTypeCache和retrievalMethodCache
      setIndexTypeCache('')
      setRetrievalMethodCache('')
    }

    setStep(step + delta)
  }, [step]) // setState函数是稳定的引用，不需要添加到依赖项中

  const checkNotionConnection = async () => {
    const { data } = await fetchDataSource({ url: '/data-source/integrates' })
    const hasConnection = data.filter(item => item.provider === 'notion') || []
    setHasConnection(hasConnection.length > 0)
  }

  useEffect(() => {
    checkNotionConnection()
  }, [])

  const [detail, setDetail] = useState<DataSet | null>(null)
  useEffect(() => {
    (async () => {
      if (datasetId) {
        try {
          const detail = await fetchDatasetDetail(datasetId)
          setDetail(detail)
        }
        catch {
          setHasError(true)
        }
      }
    })()
  }, [datasetId])

  if (hasError)
    return <AppUnavailable code={500} unknownReason={t('datasetCreation.error.unavailable') as string} />

  return (
    <div className='flex flex-col bg-components-panel-bg' style={{ height: 'calc(100vh - 56px)' }}>
      <TopBar activeIndex={step - 1} datasetId={datasetId} />
      <div style={{ height: 'calc(100% - 52px)' }}>
        {step === 1 && <StepOne
          ref={stepOneRef}
          hasConnection={hasConnection}
          onSetting={() => setShowAccountSettingModal({ payload: 'data-source' })}
          datasetId={datasetId}
          dataSourceType={dataSourceType}
          dataSourceTypeDisable={!!detail?.data_source_type}
          changeType={setDataSourceType}
          files={fileList}
          updateFile={updateFile}
          updateFileList={updateFileList}
          updateFileParseType={updateFileParseType} // 添加新方法处理解析类型变化
          notionPages={notionPages}
          updateNotionPages={updateNotionPages}
          onStepChange={nextStep}
          websitePages={websitePages}
          updateWebsitePages={setWebsitePages}
          onWebsiteCrawlProviderChange={setWebsiteCrawlProvider}
          onWebsiteCrawlJobIdChange={setWebsiteCrawlJobId}
          crawlOptions={crawlOptions}
          onCrawlOptionsChange={setCrawlOptions}
        />}
        {(step === 2 && (!datasetId || (datasetId && !!detail))) && <StepTwo
          isAPIKeySet={!!embeddingsDefaultModel}
          onSetting={() => setShowAccountSettingModal({ payload: 'provider' })}
          indexingType={detail?.indexing_technique}
          datasetId={datasetId}
          dataSourceType={dataSourceType}
          files={fileList.map(file => file.file)}
          notionPages={notionPages}
          websitePages={websitePages}
          websiteCrawlProvider={websiteCrawlProvider}
          websiteCrawlJobId={websiteCrawlJobId}
          onStepChange={changeStep}
          updateIndexingTypeCache={updateIndexingTypeCache}
          updateRetrievalMethodCache={updateRetrievalMethodCache}
          updateResultCache={updateResultCache}
          crawlOptions={crawlOptions}
        />}
        {step === 3 && <StepThree
          datasetId={datasetId}
          datasetName={detail?.name}
          indexingType={detail?.indexing_technique || indexingTypeCache}
          retrievalMethod={detail?.retrieval_model_dict?.search_method || retrievalMethodCache}
          creationCache={result}
        />}
      </div>
    </div>
  )
}

export default DatasetUpdateForm

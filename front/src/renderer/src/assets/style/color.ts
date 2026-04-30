import { theme } from 'antd'

const defaultAlgorithm = theme.getDesignToken({
  algorithm: theme.defaultAlgorithm
})

export const ANTD_SEED_TOKEN = {
  colorBgBase: defaultAlgorithm.colorBgBase, // #fff
  colorError: defaultAlgorithm.colorError, // #ff4d4f
  colorInfo: defaultAlgorithm.colorInfo, // #1677ff
  colorLink: defaultAlgorithm.colorLink, // #1677ff
  colorPrimary: defaultAlgorithm.colorPrimary, // #1677ff
  colorSuccess: defaultAlgorithm.colorSuccess, // #52c41a
  colorTextBase: defaultAlgorithm.colorTextBase, // #000
  colorWarning: defaultAlgorithm.colorWarning // #faad14
}

export const ANTD_MAP_TOKEN = {
  colorBgBlur: defaultAlgorithm.colorBgBlur, // transparent
  colorBgContainer: defaultAlgorithm.colorBgContainer, // #ffffff
  colorBgElevated: defaultAlgorithm.colorBgElevated, // #ffffff
  colorBgLayout: defaultAlgorithm.colorBgLayout, // #f5f5f5
  colorBgMask: defaultAlgorithm.colorBgMask, // rgba(0,0,0,0.45)
  colorBgSolid: defaultAlgorithm.colorBgSolid, // rgb(0,0,0)
  colorBgSolidActive: defaultAlgorithm.colorBgSolidActive, // rgba(0,0,0,0.95)
  colorBgSolidHover: defaultAlgorithm.colorBgSolidHover, // rgba(0,0,0,0.75)
  colorBgSpotlight: defaultAlgorithm.colorBgSpotlight, // rgba(0,0,0,0.85)
  colorBorder: defaultAlgorithm.colorBorder, // #d9d9d9
  colorBorderSecondary: defaultAlgorithm.colorBorderSecondary, // #f0f0f0
  colorErrorActive: defaultAlgorithm.colorErrorActive, // #d9363e
  colorErrorBg: defaultAlgorithm.colorErrorBg, // #fff2f0
  colorErrorBgActive: defaultAlgorithm.colorErrorBgActive, // #ffccc7
  colorErrorBgFilledHover: defaultAlgorithm.colorErrorBgFilledHover, // #ffdfdc
  colorErrorBgHover: defaultAlgorithm.colorErrorBgHover, // #fff1f0
  colorErrorBorder: defaultAlgorithm.colorErrorBorder, // #ffccc7
  colorErrorBorderHover: defaultAlgorithm.colorErrorBorderHover, // #ffa39e
  colorErrorHover: defaultAlgorithm.colorErrorHover, // #ff7875
  colorErrorText: defaultAlgorithm.colorErrorText, // #ff4d4f
  colorErrorTextActive: defaultAlgorithm.colorErrorTextActive, // #d9363e
  colorErrorTextHover: defaultAlgorithm.colorErrorTextHover, // #ff7875
  colorFill: defaultAlgorithm.colorFill, // rgba(0,0,0,0.15)
  colorFillQuaternary: defaultAlgorithm.colorFillQuaternary, // rgba(0,0,0,0.02)
  colorFillSecondary: defaultAlgorithm.colorFillSecondary, // rgba(0,0,0,0.06)
  colorFillTertiary: defaultAlgorithm.colorFillTertiary, // rgba(0,0,0,0.04)
  colorInfoActive: defaultAlgorithm.colorInfoActive, // #0958d9
  colorInfoBg: defaultAlgorithm.colorInfoBg, // #e6f4ff
  colorInfoBgHover: defaultAlgorithm.colorInfoBgHover, // #bae0ff
  colorInfoBorder: defaultAlgorithm.colorInfoBorder, // #91caff
  colorInfoBorderHover: defaultAlgorithm.colorInfoBorderHover, // #69b1ff
  colorInfoHover: defaultAlgorithm.colorInfoHover, // #69b1ff
  colorInfoText: defaultAlgorithm.colorInfoText, // #1677ff
  colorInfoTextActive: defaultAlgorithm.colorInfoTextActive, // #0958d9
  colorInfoTextHover: defaultAlgorithm.colorInfoTextHover, // #4096ff
  colorLinkActive: defaultAlgorithm.colorLinkActive, // #0958d9
  colorLinkHover: defaultAlgorithm.colorLinkHover, // #69b1ff
  colorPrimaryActive: defaultAlgorithm.colorPrimaryActive, // #0958d9
  colorPrimaryBg: defaultAlgorithm.colorPrimaryBg, // #e6f4ff
  colorPrimaryBgHover: defaultAlgorithm.colorPrimaryBgHover, // #bae0ff
  colorPrimaryBorder: defaultAlgorithm.colorPrimaryBorder, // #91caff
  colorPrimaryBorderHover: defaultAlgorithm.colorPrimaryBorderHover, // #69b1ff
  colorPrimaryHover: defaultAlgorithm.colorPrimaryHover, // #4096ff
  colorPrimaryText: defaultAlgorithm.colorPrimaryText, // #1677ff
  colorPrimaryTextActive: defaultAlgorithm.colorPrimaryTextActive, // #0958d9
  colorPrimaryTextHover: defaultAlgorithm.colorPrimaryTextHover, // #4096ff
  colorSuccessActive: defaultAlgorithm.colorSuccessActive, // #389e0d
  colorSuccessBg: defaultAlgorithm.colorSuccessBg, // #f6ffed
  colorSuccessBgHover: defaultAlgorithm.colorSuccessBgHover, // #d9f7be
  colorSuccessBorder: defaultAlgorithm.colorSuccessBorder, // #b7eb8f
  colorSuccessBorderHover: defaultAlgorithm.colorSuccessBorderHover, // #95de64
  colorSuccessHover: defaultAlgorithm.colorSuccessHover, // #95de64
  colorSuccessText: defaultAlgorithm.colorSuccessText, // #52c41a
  colorSuccessTextActive: defaultAlgorithm.colorSuccessTextActive, // #389e0d
  colorSuccessTextHover: defaultAlgorithm.colorSuccessTextHover, // #73d13d
  colorText: defaultAlgorithm.colorText, // rgba(0,0,0,0.88)
  colorTextQuaternary: defaultAlgorithm.colorTextQuaternary, // rgba(0,0,0,0.25)
  colorTextSecondary: defaultAlgorithm.colorTextSecondary, // rgba(0,0,0,0.65)
  colorTextTertiary: defaultAlgorithm.colorTextTertiary, // rgba(0,0,0,0.45)
  colorWarningActive: defaultAlgorithm.colorWarningActive, // #d48806
  colorWarningBg: defaultAlgorithm.colorWarningBg, // #fffbe6
  colorWarningBgHover: defaultAlgorithm.colorWarningBgHover, // #fff1b8
  colorWarningBorder: defaultAlgorithm.colorWarningBorder, // #ffe58f
  colorWarningBorderHover: defaultAlgorithm.colorWarningBorderHover, // #ffd666
  colorWarningHover: defaultAlgorithm.colorWarningHover, // #ffd666
  colorWarningText: defaultAlgorithm.colorWarningText, // #faad14
  colorWarningTextActive: defaultAlgorithm.colorWarningTextActive, // #d48806
  colorWarningTextHover: defaultAlgorithm.colorWarningTextHover, // #ffc53d
  colorWhite: defaultAlgorithm.colorWhite // #fff
}

export const ANTD_ALIAS_TOKEN = {
  colorBgContainerDisabled: defaultAlgorithm.colorBgContainerDisabled, // rgba(0,0,0,0.04)
  colorBgTextActive: defaultAlgorithm.colorBgTextActive, // rgba(0,0,0,0.15)
  colorBgTextHover: defaultAlgorithm.colorBgTextHover, // rgba(0,0,0,0.06)
  colorBorderBg: defaultAlgorithm.colorBorderBg, // #ffffff
  colorErrorOutline: defaultAlgorithm.colorErrorOutline, // rgba(255,38,5,0.06)
  colorFillAlter: defaultAlgorithm.colorFillAlter, // rgba(0,0,0,0.02)
  colorFillContent: defaultAlgorithm.colorFillContent, // rgba(0,0,0,0.06)
  colorFillContentHover: defaultAlgorithm.colorFillContentHover, // rgba(0,0,0,0.15)
  colorHighlight: defaultAlgorithm.colorHighlight, // #ff4d4f
  colorIcon: defaultAlgorithm.colorIcon, // rgba(0,0,0,0.45)
  colorIconHover: defaultAlgorithm.colorIconHover, // rgba(0,0,0,0.88)
  colorSplit: defaultAlgorithm.colorSplit, // rgba(5,5,5,0.06)
  colorTextDescription: defaultAlgorithm.colorTextDescription, // rgba(0,0,0,0.45)
  colorTextDisabled: defaultAlgorithm.colorTextDisabled, // rgba(0,0,0,0.25)
  colorTextHeading: defaultAlgorithm.colorTextHeading, // rgba(0,0,0,0.88)
  colorTextLabel: defaultAlgorithm.colorTextLabel, // rgba(0,0,0,0.65)
  colorTextLightSolid: defaultAlgorithm.colorTextLightSolid, // #fff
  colorTextPlaceholder: defaultAlgorithm.colorTextPlaceholder, // rgba(0,0,0,0.25)
  colorWarningOutline: defaultAlgorithm.colorWarningOutline, // rgba(255,215,5,0.1)
  controlInteractiveSize: defaultAlgorithm.controlInteractiveSize, // 16
  controlItemBgActive: defaultAlgorithm.controlItemBgActive, // #e6f4ff
  controlItemBgActiveDisabled: defaultAlgorithm.controlItemBgActiveDisabled, // rgba(0,0,0,0.15)
  controlItemBgActiveHover: defaultAlgorithm.controlItemBgActiveHover, // #bae0ff
  controlItemBgHover: defaultAlgorithm.controlItemBgHover, // rgba(0,0,0,0.04)
  controlOutline: defaultAlgorithm.controlOutline // rgba(5,145,255,0.1)
}

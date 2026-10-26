#!/usr/bin/env python3
"""
Genera `Dinamico.tdesktop-theme` para Materialgram (fork de Telegram
Desktop) a partir del Accent de KDE.

Plantilla: tema "SolidDark" de MasterGroosha (MIT,
https://github.com/MasterGroosha/telegram-soliddark-theme). Se conserva
su cabecera/atribución; solo se sustituyen las variables de color y los
hex inline marcados con el accent derivado de KDE. Los colores
semánticos (estados de peers 1-8, online, errores) se dejan intactos.

Importación (única vez): enviar ~/Documents/Dinamico.tdesktop-theme a
"Mensajes guardados", tocar la burbuja -> Aplicar. Aparece en
"Temas personalizados". Telegram no recarga el archivo en vivo: tras
cada cambio de accent, re-tocar "Dinamico" en la lista (sin reiniciar).
"""
import colorsys
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge import get_accent_rgb, hsv_to_hex

DESTINOS = [
    os.path.expanduser("~/.var/app/io.github.kukuruzka165.materialgram/data/materialgram/tdata/Dinamico.tdesktop-theme"),
    os.path.expanduser("~/.config/materialgram/themes/Dinamico.tdesktop-theme"),
    os.path.expanduser("~/Documents/Dinamico.tdesktop-theme"),
]

# Plantilla completa con la estructura real de un .tdesktop-theme.
# Los valores de accent/fondo se sustituyen en main(); el resto queda
# tal cual (claves semánticas, peers, etc.).
TEMPLATE = """//////////////////////////////////////////////////////////////////////////////////////////////////
//                                                                                              //
//                          SolidDark theme v1.2 for Telegram Desktop.                          //
//                          (plantilla MIT de MasterGroosha)                                    //
//                 Colores generados del accent KDE por generate_materialgram_theme.py           //
//                                                                                              //
//////////////////////////////////////////////////////////////////////////////////////////////////

// Color presets //

COLOR_GRAY: #999999;
COLOR_DARK: #392F3C;
COLOR_PURPLE_DARK: #9876AD;
COLOR_PURPLE_LIGHT: #9151A6;
COLOR_PURPLE_RIPPLE_ACTIVE: #787BAC;

COLOR_WHITE: #ffffff;
COLOR_BLACK: #000000;
COLOR_PINK: #e016a0;
COLOR_HOVER: #424444;


// basic
windowBg: COLOR_DARK;
windowFg: COLOR_WHITE;
windowBgOver: #3A2F3E;
windowBgRipple: #272828;
windowFgOver: windowFg;
windowSubTextFg: COLOR_GRAY;
windowSubTextFgOver: #919191;
windowBoldFg: COLOR_WHITE;
windowBoldFgOver: COLOR_PURPLE_LIGHT;
windowBgActive: COLOR_PURPLE_DARK;
windowFgActive: COLOR_WHITE;
windowActiveTextFg: COLOR_PURPLE_LIGHT;
windowShadowFg: COLOR_BLACK;
windowShadowFgFallback: COLOR_DARK;

shadowFg: #00000018;
slideFadeOutBg: #0000003c;
slideFadeOutShadowFg: windowShadowFg;

imageBg: COLOR_BLACK;
imageBgTransparent: COLOR_WHITE;

//widgets
activeButtonBg: COLOR_PURPLE_DARK;
activeButtonBgOver: #908FAE;
activeButtonBgRipple: COLOR_PURPLE_RIPPLE_ACTIVE;
activeButtonFg: COLOR_WHITE;
activeButtonFgOver: activeButtonFg;
activeButtonSecondaryFg: COLOR_WHITE;
activeButtonSecondaryFgOver: COLOR_WHITE;
activeLineFg: COLOR_PURPLE_DARK;
activeLineFgError: #e48383;

lightButtonBg: COLOR_DARK;
lightButtonBgOver: #424444;
lightButtonBgRipple: #3A2F3E;
lightButtonFg: COLOR_WHITE;
lightButtonFgOver: lightButtonFg;

attentionButtonFg: #d84343;
attentionButtonFgOver: #d84343;
attentionButtonBgOver: #ef9592;
attentionButtonBgRipple: #d87c79;

outlineButtonBg: COLOR_DARK;
outlineButtonBgOver: lightButtonBgOver;
outlineButtonOutlineFg: windowBgActive;
outlineButtonBgRipple: lightButtonBgRipple;

menuBg: COLOR_DARK;
menuBgOver: windowBgOver;
menuBgRipple: windowBgRipple;
menuIconFg: COLOR_GRAY;
menuIconFgOver: COLOR_PURPLE_LIGHT;
menuSubmenuArrowFg: #373737;
menuFgDisabled: #cccccc;
menuSeparatorFg: COLOR_DARK;

scrollBarBg: #15cd7d53;
scrollBarBgOver: #15cd7d7a;
scrollBg: #0000001a;
scrollBgOver: #0000002c;

smallCloseIconFg: #c7c7c7;
smallCloseIconFgOver: #a3a3a3;

radialFg: COLOR_WHITE;
radialBg: #00000056;

placeholderFg: COLOR_GRAY;
placeholderFgActive: #aaaaaa;
inputBorderFg: #e0e0e0;
filterInputBorderFg: COLOR_PURPLE_DARK;
filterInputInactiveBg: windowBgOver;
checkboxFg: #b3b3b3;

sliderBgInactive: #e1eaef;
sliderBgActive: windowBgActive;

tooltipBg: #eef2f5;
tooltipFg: #5d6c80;
tooltipBorderFg: #c9d1db;


// custom title bar for Windows and macOS
titleBg: COLOR_DARK;
titleBgActive: titleBg;
titleButtonBg: titleBg;
titleShadow: #00000003;
titleButtonFg: #ababab;
titleButtonBgOver: #dbdbdb;
titleButtonFgOver: #9a9a9a;
titleButtonBgActive: titleButtonBg;
titleButtonFgActive: titleButtonFg;
titleButtonBgActiveOver: titleButtonBgOver;
titleButtonFgActiveOver: titleButtonFgOver;
titleButtonCloseBg: titleButtonBg;
titleButtonCloseFg: titleButtonFg;
titleButtonCloseBgOver: #e81123;
titleButtonCloseFgOver: COLOR_WHITE;
titleButtonCloseBgActive: titleButtonCloseBg;
titleButtonCloseFgActive: titleButtonCloseFg;
titleButtonCloseBgActiveOver: titleButtonCloseBgOver;
titleButtonCloseFgActiveOver: titleButtonCloseFgOver;
titleFgActive: #3e3c3e;
titleFg: #acacac;

// tray icon
trayCounterBg: #f23c34;
trayCounterBgMute: #888888;
trayCounterFg: COLOR_WHITE;
trayCounterBgMacInvert: COLOR_WHITE;
trayCounterFgMacInvert: COLOR_WHITE;

// layers
layerBg: #0000007f;

cancelIconFg: menuIconFg;
cancelIconFgOver: menuIconFgOver;

// boxes
boxBg: COLOR_DARK;
boxTextFg: COLOR_GRAY;
boxTextFgGood: #6E88AD;
boxTextFgError: #d84d4d;
boxTitleFg: COLOR_WHITE;
boxSearchBg: boxBg;
boxSearchCancelIconFg: cancelIconFg;
boxSearchCancelIconFgOver: cancelIconFgOver;

boxTitleAdditionalFg: #808080;
boxTitleCloseFg: cancelIconFg;
boxTitleCloseFgOver: cancelIconFgOver;

membersAboutLimitFg: windowSubTextFgOver;

contactsBg: COLOR_DARK;
contactsBgOver: windowBgOver;
contactsNameFg: COLOR_WHITE;
contactsStatusFg: COLOR_GRAY;
contactsStatusFgOver: windowSubTextFgOver;
contactsStatusFgOnline: windowActiveTextFg;

photoCropFadeBg: layerBg;
photoCropPointFg: COLOR_WHITE;

// intro
introBg: COLOR_DARK;
introTitleFg: windowBoldFg;
introDescriptionFg: COLOR_GRAY;
introErrorFg: COLOR_GRAY;

introCoverTopBg: COLOR_DARK;
introCoverBottomBg: COLOR_DARK;
introCoverIconsFg: COLOR_PURPLE_DARK;
introCoverPlaneTrace: #15cd7d69;
introCoverPlaneInner: #c6d8e8;
introCoverPlaneOuter: #a1bed4;
introCoverPlaneTop: COLOR_WHITE;

dialogsMenuIconFg: menuIconFg;
dialogsMenuIconFgOver: menuIconFgOver;

dialogsBg: COLOR_DARK;
dialogsNameFg: COLOR_WHITE;
dialogsChatIconFg: dialogsNameFg;
dialogsDateFg: COLOR_GRAY;
dialogsTextFg: COLOR_GRAY;
dialogsTextFgService: windowActiveTextFg;
dialogsDraftFg: #dd4b39;
dialogsVerifiedIconBg: windowBgActive;
dialogsVerifiedIconFg: COLOR_WHITE;
dialogsSendingIconFg: #c1c1c1;
dialogsSentIconFg: #6972AA;
dialogsUnreadBg: COLOR_PURPLE_DARK;
dialogsUnreadBgMuted: #999999;
dialogsUnreadFg: COLOR_WHITE;

dialogsBgOver: #3A2F3E;
dialogsNameFgOver: #ededed;
dialogsChatIconFgOver: dialogsNameFgOver;
dialogsDateFgOver: windowSubTextFgOver;
dialogsTextFgOver: windowSubTextFgOver;
dialogsTextFgServiceOver: dialogsTextFgService;
dialogsDraftFgOver: dialogsDraftFg;
dialogsVerifiedIconBgOver: dialogsVerifiedIconBg;
dialogsVerifiedIconFgOver: dialogsVerifiedIconFg;
dialogsSendingIconFgOver: dialogsSendingIconFg;
dialogsSentIconFgOver: dialogsSentIconFg;
dialogsUnreadBgOver: dialogsUnreadBg;
dialogsUnreadBgMutedOver: dialogsUnreadBgMuted;
dialogsUnreadFgOver: dialogsUnreadFg;

dialogsBgActive: COLOR_PURPLE_DARK;
dialogsNameFgActive: COLOR_WHITE;
dialogsChatIconFgActive: dialogsNameFgActive;
dialogsDateFgActive: COLOR_WHITE;
dialogsTextFgActive: COLOR_WHITE;
dialogsTextFgServiceActive: dialogsTextFgActive;
dialogsDraftFgActive: #c6e1f7;
dialogsVerifiedIconBgActive: dialogsTextFgActive;
dialogsVerifiedIconFgActive: dialogsBgActive;
dialogsSendingIconFgActive: COLOR_WHITE;
dialogsSentIconFgActive: dialogsTextFgActive;
dialogsUnreadBgActive: dialogsTextFgActive;
dialogsUnreadBgMutedActive: dialogsDraftFgActive;
dialogsUnreadFgActive: dialogsBgActive;

dialogsForwardBg: dialogsBgActive;
dialogsForwardFg: dialogsNameFgActive;

searchedBarBg: COLOR_DARK;
searchedBarBorder: COLOR_PURPLE_DARK;
searchedBarFg: COLOR_PURPLE_LIGHT;

// history
historyBg: COLOR_DARK;
topBarBg: COLOR_DARK;
emojiPanBg: COLOR_DARK;
emojiPanCategories: COLOR_DARK;
emojiPanHeaderFg: COLOR_PURPLE_LIGHT;
emojiPanHeaderBg: COLOR_DARK;
stickerPanDeleteBg: #000000cc;
stickerPanDeleteFg: COLOR_WHITE;
stickerPreviewBg: #2f2f2fCC;

historyTextInFg: #adadad;
historyTextOutFg: #efefef;
historyCaptionInFg: historyTextInFg;
historyCaptionOutFg: historyTextOutFg;
historyFileNameInFg: historyTextInFg;
historyFileNameOutFg: historyTextOutFg;
historyOutIconFg: dialogsSentIconFg;
historyOutIconFgSelected: COLOR_PURPLE_LIGHT;
historyIconFgInverted: COLOR_WHITE;
historySendingOutIconFg: #98d292;
historySendingInIconFg: #a0adb5;
historySendingInvertedIconFg: COLOR_WHITE;

historySystemBg: #89a0b47f;
historySystemBgSelected: #bbc8d4a2;
historySystemFg: COLOR_WHITE;

historyUnreadBarBg: #424444;
historyUnreadBarBorder: COLOR_DARK;
historyUnreadBarFg: #ededed;

historyForwardChooseBg: #0000004c;
historyForwardChooseFg: COLOR_WHITE;

historyPeer1NameFg: #ff9100;
historyPeer1UserpicBg: #e17076;
historyPeer2NameFg: #4fad2d;
historyPeer2UserpicBg: #7bc862;
historyPeer3NameFg: #d09306;
historyPeer3UserpicBg: #e5ca77;
historyPeer4NameFg: #15cd7d;
historyPeer4UserpicBg: #65aadd;
historyPeer5NameFg: #a363f2;
historyPeer5UserpicBg: #a695e7;
historyPeer6NameFg: #cd4073;
historyPeer6UserpicBg: #ee7aae;
historyPeer7NameFg: #2996ad;
historyPeer7UserpicBg: #6ec9cb;
historyPeer8NameFg: #ce671b;
historyPeer8UserpicBg: #faa774;
historyPeerUserpicFg: COLOR_WHITE;

historyScrollBarBg: #9876AD7a;
historyScrollBarBgOver: #9876ADbc;
historyScrollBg: #6f72724d;
historyScrollBgOver: #6f727280;

msgInBg: #A195AE24;
msgInBgSelected: #222323;
msgOutBg: #9976AD24;
msgOutBgSelected: #222323;
msgSelectOverlay: #2223239b;
msgStickerOverlay: #2223237f;
msgInServiceFg: windowActiveTextFg;
msgInServiceFgSelected: windowActiveTextFg;
msgOutServiceFg: COLOR_PURPLE_LIGHT;
msgOutServiceFgSelected: #367570;
msgInShadow: #3d3c3c29;
msgInShadowSelected: #2f303029;
msgOutShadow: #4e4f4e40;
msgOutShadowSelected: #2f303040;
msgInDateFg: #a0acb6;
msgInDateFgSelected: COLOR_PURPLE_LIGHT;
msgOutDateFg: COLOR_GRAY;
msgOutDateFgSelected: COLOR_PURPLE_LIGHT;
msgServiceFg: COLOR_WHITE;
msgServiceBg: #607D8B7f;
msgServiceBgSelected: #8ca0b3a2;
msgInReplyBarColor: COLOR_PURPLE_DARK;
msgInReplyBarSelColor: COLOR_PURPLE_DARK;
msgOutReplyBarColor: COLOR_PURPLE_DARK;
msgOutReplyBarSelColor: COLOR_PURPLE_DARK;
msgInMonoFg: COLOR_PURPLE_LIGHT;
msgOutMonoFg: COLOR_PURPLE_LIGHT;
msgDateImgFg: msgServiceFg;
msgDateImgBg: #00000054;
msgDateImgBgOver: #00000074;
msgDateImgBgSelected: #1c4a7187;

msgFileThumbLinkInFg: lightButtonFg;
msgFileThumbLinkInFgSelected: lightButtonFgOver;
msgFileThumbLinkOutFg: #5eba5b;
msgFileThumbLinkOutFgSelected: #31a298;
msgFileInBg: windowBgActive;
msgFileInBgOver: #63b56a;
msgFileInBgSelected: #63b56a;
msgFileOutBg: COLOR_PURPLE_DARK;
msgFileOutBgOver: #6bc272;
msgFileOutBgSelected: #5fb389;

msgFile1Bg: #72b1df;
msgFile1BgDark: #5c9ece;
msgFile1BgOver: #5294c4;
msgFile1BgSelected: #5099d0;
msgFile2Bg: #61b96e;
msgFile2BgDark: #4da859;
msgFile2BgOver: #44a050;
msgFile2BgSelected: #46a07e;
msgFile3Bg: #e47272;
msgFile3BgDark: #cd5b5e;
msgFile3BgOver: #c35154;
msgFile3BgSelected: #9f6a82;
msgFile4Bg: #efc274;
msgFile4BgDark: #e6a561;
msgFile4BgOver: #dc9c5a;
msgFile4BgSelected: #b19d84;

historyFileInIconFg: COLOR_WHITE;
historyFileInIconFgSelected: COLOR_WHITE;
historyFileInRadialFg: COLOR_WHITE;
historyFileInRadialFgSelected: COLOR_WHITE;
historyFileOutIconFg: COLOR_WHITE;
historyFileOutIconFgSelected: COLOR_WHITE;
historyFileOutRadialFg: COLOR_WHITE;
historyFileOutRadialFgSelected: COLOR_WHITE;
historyFileThumbIconFg: COLOR_WHITE;
historyFileThumbIconFgSelected: COLOR_WHITE;
historyFileThumbRadialFg: COLOR_WHITE;
historyFileThumbRadialFgSelected: COLOR_WHITE;

msgWaveformInActive: windowBgActive;
msgWaveformInActiveSelected: COLOR_PURPLE_LIGHT;
msgWaveformInInactive: #d4dee6;
msgWaveformInInactiveSelected: COLOR_WHITE;
msgWaveformOutActive: windowBgActive;
msgWaveformOutActiveSelected: COLOR_PURPLE_LIGHT;
msgWaveformOutInactive: COLOR_WHITE;
msgWaveformOutInactiveSelected: COLOR_WHITE;

msgBotKbOverBgAdd: COLOR_DARK;
msgBotKbIconFg: COLOR_WHITE;
msgBotKbRippleBg: #00000020;

mediaInFg: msgInDateFg;
mediaInFgSelected: msgInDateFgSelected;
mediaOutFg: msgOutDateFg;
mediaOutFgSelected: msgOutDateFgSelected;

youtubePlayIconBg: #e83131c8;
youtubePlayIconFg: COLOR_WHITE;
videoPlayIconBg: #0000007f;
videoPlayIconFg: COLOR_WHITE;
toastBg: #000000b2;
toastFg: COLOR_WHITE;

reportSpamBg: emojiPanHeaderBg;
reportSpamFg: COLOR_GRAY;

historyToDownBg: #424444;
historyToDownBgOver: windowBgOver;
historyToDownBgRipple: windowBgRipple;
historyToDownFg: menuIconFg;
historyToDownFgOver: menuIconFgOver;
historyToDownShadow: #00000040;
historyComposeAreaBg: msgInBg;
historyComposeAreaFg: COLOR_WHITE;
historyComposeAreaFgService: msgInDateFg;
historyComposeIconFg: menuIconFg;
historyComposeIconFgOver: menuIconFgOver;
historySendIconFg: windowBgActive;
historySendIconFgOver: windowBgActive;
historyPinnedBg: historyComposeAreaBg;
historyReplyBg: historyComposeAreaBg;
historyReplyCancelFg: cancelIconFg;
historyReplyCancelFgOver: cancelIconFgOver;

historyComposeButtonBg: historyComposeAreaBg;
historyComposeButtonBgOver: windowBgOver;
historyComposeButtonBgRipple: windowBgRipple;

// overview
overviewCheckBg: #00000040;
overviewCheckFg: COLOR_DARK;
overviewCheckFgActive: COLOR_DARK;
overviewPhotoSelectOverlay: #40ace333;
profileStatusFgOver: #7c99b2;
profileVerifiedCheckBg: windowBgActive;
profileVerifiedCheckFg: windowFgActive;
profileAdminStartFg: COLOR_PURPLE_LIGHT;
notificationsBoxMonitorFg: COLOR_GRAY;
notificationsBoxScreenBg: dialogsBgActive;
notificationSampleUserpicFg: windowBgActive;
notificationSampleCloseFg: #d7d7d7;
notificationSampleTextFg: #d7d7d7;
notificationSampleNameFg: #939393;

mainMenuBg: COLOR_DARK;
mainMenuCoverBg: dialogsBgActive;
mainMenuCoverFg: COLOR_WHITE;
mediaPlayerBg: COLOR_DARK;
mediaPlayerActiveFg: COLOR_PURPLE_DARK;
mediaPlayerInactiveFg: #4f5151;
mediaPlayerDisabledFg: #9dd1ef;
mediaviewFileBg: COLOR_DARK;
mediaviewFileNameFg: COLOR_GRAY;
mediaviewFileSizeFg: COLOR_GRAY;
mediaviewFileRedCornerFg: #d55959;
mediaviewFileYellowCornerFg: #e8a659;
mediaviewFilePurpleCornerFg: #49a957;
mediaviewFileBlueCornerFg: #599dcf;
mediaviewFileExtFg: activeButtonFg;
mediaviewMenuBg: #383838;
mediaviewMenuBgOver: #505050;
mediaviewMenuBgRipple: #676767;
mediaviewMenuFg: COLOR_WHITE;
mediaviewBg: #222222eb;
mediaviewVideoBg: imageBg;
mediaviewControlBg: #0000003c;
mediaviewControlFg: COLOR_WHITE;
mediaviewCaptionBg: #11111180;
mediaviewCaptionFg: mediaviewControlFg;
mediaviewTextLinkFg: #91d9ff;
mediaviewSaveMsgBg: toastBg;
mediaviewSaveMsgFg: toastFg;
mediaviewPlaybackActive: #c7c7c7;
mediaviewPlaybackInactive: #252525;
mediaviewPlaybackActiveOver: COLOR_WHITE;
mediaviewPlaybackInactiveOver: #474747;
mediaviewPlaybackProgressFg: COLOR_WHITE;
mediaviewPlaybackIconFg: mediaviewPlaybackActive;
mediaviewPlaybackIconFgOver: mediaviewPlaybackActiveOver;
mediaviewTransparentBg: COLOR_WHITE;
mediaviewTransparentFg: #cccccc;
notificationBg: COLOR_DARK;

// folder sidebar (columna de carpetas: Todos/Personales/Editar)
sideBarBg: COLOR_DARK;
sideBarBgActive: COLOR_HOVER;
sideBarBgRipple: windowBgRipple;
sideBarTextFg: COLOR_GRAY;
sideBarTextFgActive: COLOR_PURPLE_LIGHT;
sideBarIconFg: COLOR_GRAY;
sideBarIconFgActive: COLOR_PURPLE_DARK;
sideBarBadgeBg: COLOR_PURPLE_DARK;
sideBarBadgeBgMuted: COLOR_GRAY;
sideBarBadgeFg: COLOR_WHITE;
"""


def main():
    r, g, b = get_accent_rgb()
    h, s, v = colorsys.rgb_to_hsv(r, g, b)

    bg = hsv_to_hex(h, min(0.30, s), 0.10)
    bg_over = hsv_to_hex(h, min(0.30, s), 0.16)
    bg_over2 = hsv_to_hex(h, min(0.30, s), 0.21)
    fg = hsv_to_hex(h, min(0.04, s), 0.93)
    grey = hsv_to_hex(h, min(0.12, s), 0.60)
    accent = hsv_to_hex(h, s, v)
    accent_light = hsv_to_hex(h, max(0.15, s - 0.15), min(1.0, v + 0.08))
    accent_pressed = hsv_to_hex(h, min(1.0, s + 0.05), max(0.20, v - 0.18))
    env = os.environ.get
    bg, bg_over, bg_over2 = env("MATUGEN_BG", bg), env("MATUGEN_BG_OVER", bg_over), env("MATUGEN_BG_OVER2", bg_over2)
    fg, grey = env("MATUGEN_FG", fg), env("MATUGEN_GREY", grey)
    accent = env("MATUGEN_ACCENT", accent)
    accent_light, accent_pressed = env("MATUGEN_ACCENT_LIGHT", accent_light), env("MATUGEN_ACCENT_PRESSED", accent_pressed)

    content = TEMPLATE
    subs = {
        # Variables de la plantilla -> paleta KDE
        "COLOR_GRAY: #999999;": f"COLOR_GRAY: {grey};",
        "COLOR_DARK: #392F3C;": f"COLOR_DARK: {bg};",
        "COLOR_PURPLE_DARK: #9876AD;": f"COLOR_PURPLE_DARK: {accent};",
        "COLOR_PURPLE_LIGHT: #9151A6;": f"COLOR_PURPLE_LIGHT: {accent_light};",
        "COLOR_PURPLE_RIPPLE_ACTIVE: #787BAC;": f"COLOR_PURPLE_RIPPLE_ACTIVE: {accent_pressed};",
        "COLOR_WHITE: #ffffff;": f"COLOR_WHITE: {fg};",
        "COLOR_PINK: #e016a0;": f"COLOR_PINK: {accent};",
        # Hex inline de la plantilla (hovers, scrollbars, burbujas)
        "#3A2F3E": bg_over,        # windowBgOver, dialogsBgOver, lightButtonBgRipple
        "#424444": bg_over2,       # lightButtonBgOver, historyUnreadBarBg, historyToDownBg
        "#908FAE": accent_light,   # activeButtonBgOver
        "#9876AD7a": f"{accent}7a",  # historyScrollBarBg
        "#9876ADbc": f"{accent}bc",  # historyScrollBarBgOver
        "#A195AE24": bg_over,        # msgInBg (burbuja entrante, neutra, SOLIDA)
        "#9976AD24": accent_pressed,  # msgOutBg (burbuja saliente, accent, SOLIDA)
    }
    for old, new in subs.items():
        content = content.replace(old, new)

    for dest in DESTINOS:
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w") as f:
                f.write(content)
            print(f"Materialgram: tema escrito en {dest} (accent {accent}).")
        except OSError as e:
            print(f"Materialgram: no se pudo escribir {dest}: {e}")


if __name__ == "__main__":
    main()

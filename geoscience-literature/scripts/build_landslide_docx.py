#!/usr/bin/env python3
"""Generate three landslide-domain Word literature documents."""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

OUT_DIR = Path(__file__).resolve().parent.parent / "word"


def _style_doc(doc: Document) -> None:
    style = doc.styles["Normal"]
    style.font.name = "宋体"
    style.font.size = Pt(12)


def _title(doc: Document, text: str, subtitle: str = "") -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(16)
    if subtitle:
        p2 = doc.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(subtitle)
        r2.font.size = Pt(11)
    doc.add_paragraph()


def doc_rainfall_landslide() -> None:
    doc = Document()
    _style_doc(doc)
    _title(
        doc,
        "降雨诱发型滑坡机理与预警研究综述",
        "地质滑坡领域文献资料 · 专题综述（一）",
    )

    sections = [
        (
            "摘要",
            "降雨是诱发浅层土质滑坡与岩质滑坡复活的最主要外动力因素之一。"
            "本文综述了降雨入渗—基质吸力变化—抗剪强度弱化—失稳启动的链式机理，"
            "总结了临界降雨强度—历时模型、地下水位耦合效应及基于雨量站的预警框架，"
            "并对机器学习融合多源遥感监测的应用前景进行了评述。",
        ),
        (
            "1 研究背景",
            "我国西南、华南及东南丘陵区降雨充沛，滑坡灾害呈现“季节性集中、群发性突出”特征。"
            "2008 年汶川地震后，震区松散物源与降雨叠加导致滑坡活动显著增强；"
            "近年来极端降水事件频发，小时强降雨触发的浅层滑坡对交通干线、村镇及水电设施构成严重威胁。",
        ),
        (
            "2 降雨诱发机理",
            "（1）入渗增重：雨水进入坡体后增加自重，降低有效应力。\n"
            "（2）孔隙水压力上升：饱和带扩大，库仑抗剪强度τf = c' + (σ - u) tanφ' 中 u 增大。\n"
            "（3）基质吸力丧失：非饱和带吸力下降，土体抗剪强度迅速弱化。\n"
            "（4）渗流力作用：坡脚出渗带形成渗透力，促进滑面贯通。\n"
            "典型实验手段包括室内变水头渗透试验、降雨模拟槽试验及现场渗压计监测。",
        ),
        (
            "3 预警模型与指标",
            "国际常用 I-D（强度—历时）阈值曲线与有效降雨累积量指标；"
            "国内学者结合地区雨量特征提出分级预警：注意、警戒、警报、撤离。"
            "近年来将土壤含水量、InSAR 形变速率、裂缝计数据纳入综合预警指数，"
            "提高了对蠕变—加速—破坏三阶段演化的识别能力。",
        ),
        (
            "4 典型案例",
            "• 香港天然山坡：高密度城市下短历时暴雨滑坡预警体系。\n"
            "• 三峡库区：库水位变动与降雨联合作用下的库岸滑坡。\n"
            "• 四川茂县—汶川走廊：震后松散堆积体降雨型群发性滑坡。",
        ),
        (
            "5 研究展望",
            "需加强高时空分辨率降雨预报与坡体水文模型耦合；"
            "发展基于物理信息神经网络（PINN）的滑坡易发性动态评价；"
            "完善“隐患点—监测站—群测群防”一体化数据共享平台。",
        ),
        (
            "参考文献（节选）",
            "[1] Iverson R M. Landslide triggering by rain infiltration. Water Resources Research, 2000.\n"
            "[2] 黄润秋. 20世纪以来中国大陆的重大地质灾害事件. 西南交通大学学报, 2009.\n"
            "[3] Aleotti P, Chowdhury R. Landslide hazard assessment. Engineering Geology, 1999.\n"
            "[4] 许强等. 滑坡灾害研究进展与展望. 地质学报, 2022.",
        ),
    ]
    for heading, body in sections:
        doc.add_heading(heading, level=1)
        doc.add_paragraph(body)

    doc.save(OUT_DIR / "01-降雨诱发型滑坡机理与预警研究综述.docx")


def doc_insar_landslide() -> None:
    doc = Document()
    _style_doc(doc)
    _title(
        doc,
        "西南山地滑坡隐患识别与InSAR监测技术应用",
        "地质滑坡领域文献资料 · 技术综述（二）",
    )

    sections = [
        (
            "摘要",
            "西南高山峡谷区地形陡峻、植被覆盖差异大、云雨天气频繁，传统地面调查难以实现滑坡隐患的全域普查。"
            "本文介绍合成孔径雷达干涉测量（InSAR）及时间序列 InSAR（TS-InSAR、PS-InSAR、SBAS）"
            "在滑坡蠕变识别、活动性分级和监测预警中的技术流程、精度限制与典型应用案例。",
        ),
        (
            "1 区域地质背景",
            "青藏高原东缘向四川盆地过渡带，新构造运动强烈，断裂发育，地震活动频繁。"
            "变质岩、碎裂岩、松散堆积体及残坡积层分布广泛，为滑坡形成提供了丰富的物质基础和不利结构面组合。",
        ),
        (
            "2 InSAR 技术原理",
            "InSAR 通过两景 SAR 影像相位差提取地表沿视线方向（LOS）形变。"
            "时间序列方法可克服大气延迟、轨道误差与植被去相干问题，"
            "实现毫米—厘米级年形变速率制图，识别缓慢蠕变型滑坡隐患。",
        ),
        (
            "3 隐患识别技术路线",
            "（1）多轨道、多传感器数据获取（Sentinel-1、ALOS-2 等）。\n"
            "（2）DEM 辅助的坡度、曲率、岩性因子叠加分析。\n"
            "（3）形变异常区与历史滑坡编目、光学影像解译交叉验证。\n"
            "（4）结合无人机 LiDAR 与地质测绘进行野外核查。",
        ),
        (
            "4 监测预警应用",
            "对重大隐患点建立 InSAR + GNSS + 裂缝计综合监测网；"
            "设定形变速率阈值与加速度指标，服务水库、铁路、输电走廊运维管理。"
            "需注意坡向与卫星视线夹角造成的几何畸变及河谷地区大气延迟误差。",
        ),
        (
            "5 存在问题与建议",
            "植被茂密区相干性低、升轨/降轨数据融合不足、三维形变分解精度有限。"
            "建议加强 L 波段 SAR、国产卫星数据应用及 InSAR 成果与数值模拟（如无限边坡、渗流—稳定性耦合）的联合验证。",
        ),
        (
            "参考文献（节选）",
            "[1] Wasowski J, Bovenga F. Investigating landslides with space-borne SAR. Earth-Science Reviews, 2014.\n"
            "[2] 张勤等. 地质灾害 InSAR 监测技术进展. 武汉大学学报（信息科学版）, 2020.\n"
            "[3] Carlà T et al. Integration of ground-based radar and satellite InSAR data. Remote Sensing, 2019.",
        ),
    ]
    for heading, body in sections:
        doc.add_heading(heading, level=1)
        doc.add_paragraph(body)

    doc.save(OUT_DIR / "02-西南山地滑坡隐患识别与InSAR监测技术应用.docx")


def doc_reservoir_landslide() -> None:
    doc = Document()
    _style_doc(doc)
    _title(
        doc,
        "库岸滑坡—水体耦合失稳与防治工程述评",
        "地质滑坡领域文献资料 · 工程综述（三）",
    )

    sections = [
        (
            "摘要",
            "水库蓄水后，库岸斜坡受水位波动、浸润线变化、渗透压力及波浪冲刷共同影响，"
            "易诱发老滑坡复活与新滑坡形成。本文评述库岸滑坡变形阶段划分、"
            "稳定性分析方法及排水、支挡、锚固、抗滑桩等防治工程措施的适用条件。",
        ),
        (
            "1 库岸滑坡类型",
            "按成因可分为：蓄水诱发型、水位骤降型、浪蚀型、地震—库水耦合型。"
            "按物质组成可分为土质滑坡、岩质滑坡与堆积层滑坡。"
            "三峡库区、溪洛渡—向家坝库区是我国库岸滑坡研究与工程治理的重点区域。",
        ),
        (
            "2 水体—坡体耦合机理",
            "蓄水后：坡脚浸润线抬升，抗滑力下降；浮托力与渗透压力增大。\n"
            "水位骤降：坡体内部渗透压力滞后于库水位，形成向坡外渗流梯度，易触发滑坡。\n"
            "数值模拟常采用 SEEP/W 与 SLOPE/W、FLAC3D 等软件进行渗流—稳定性联合分析。",
        ),
        (
            "3 稳定性评价方法",
            "极限平衡法（Bishop、Spencer 等）、强度折减法及可靠度分析广泛应用于库岸滑坡。"
            "评价需考虑库水位变幅、暴雨工况、地震工况的组合，"
            "并关注滑带土残余强度参数选取对安全系数 Fs 的敏感性。",
        ),
        (
            "4 防治工程措施",
            "（1）地表排水与仰斜排水孔：降低孔隙水压力。\n"
            "（2）重力式挡墙、抗滑桩：提高抗滑力。\n"
            "（3）预应力锚索：加固岩质库岸与高陡边坡。\n"
            "（4）护岸与防浪结构：减轻浪蚀与冲刷。\n"
            "工程布置应兼顾蓄水运行、生态景观与长期监测需求。",
        ),
        (
            "5 管理与监测",
            "建立库岸滑坡数据库，实施分级分类管理；"
            "布设地下水位计、渗压计、位移计与视频监控；"
            "将防治工程纳入水库调度与应急抢险预案。",
        ),
        (
            "参考文献（节选）",
            "[1] Schuster R L, Alford D. Upland landslide response to the 2008 Wenchuan earthquake. Landslides, 2008.\n"
            "[2] 王士天等. 三峡库区滑坡研究与防治. 地质出版社相关专著.\n"
            "[3] Londe P. The Malpasset Dam failure. Engineering Geology, 1987.",
        ),
    ]
    for heading, body in sections:
        doc.add_heading(heading, level=1)
        doc.add_paragraph(body)

    doc.save(OUT_DIR / "03-库岸滑坡水体耦合失稳与防治工程述评.docx")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc_rainfall_landslide()
    doc_insar_landslide()
    doc_reservoir_landslide()
    print(f"Created 3 Word documents in {OUT_DIR}")


if __name__ == "__main__":
    main()

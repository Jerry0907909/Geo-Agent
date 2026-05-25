# 地球科学文献资料库

本目录存放 Geo-Agent 项目配套的地球科学专题学习资料，可用于文档导入、RAG 检索测试与教学参考。

## 目录结构

```
geoscience-literature/
├── word/          # 地质滑坡领域 Word 文献（.docx）
├── markdown/      # 地球科学专题 Markdown 资料
├── scripts/       # Word 文档生成脚本
└── README.md
```

## Word 文档（地质滑坡）

| 文件 | 主题 |
|------|------|
| `01-降雨诱发型滑坡机理与预警研究综述.docx` | 降雨入渗机理、预警模型与典型案例 |
| `02-西南山地滑坡隐患识别与InSAR监测技术应用.docx` | InSAR/TS-InSAR 隐患识别与监测 |
| `03-库岸滑坡水体耦合失稳与防治工程述评.docx` | 库岸滑坡机理与防治工程 |

## Markdown 文档（地球科学）

| 文件 | 主题 |
|------|------|
| `01-板块构造与大陆动力学基础.md` | 板块边界、大陆动力学与灾害背景 |
| `02-深部地幔柱与热点火山成因.md` | 地幔柱假说与热点火山 |
| `03-沉积盆地演化与储层地球化学.md` | 盆地演化、成岩作用与储层地球化学 |

## 重新生成 Word 文档

```bash
python geoscience-literature/scripts/build_landslide_docx.py
```

## 导入 Geo-Agent 知识库

```bash
python scripts/import_documents.py --dir ./geoscience-literature
```

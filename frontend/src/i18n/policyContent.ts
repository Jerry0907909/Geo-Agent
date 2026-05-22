import type { Language } from "./types"

export interface PolicySection {
  heading: string
  body: string
}

export interface PolicyDocument {
  title: string
  intro: string
  sections: PolicySection[]
}

export type PolicyKey = "terms" | "privacy" | "sources"

const zhCN: Record<PolicyKey, PolicyDocument> = {
  terms: {
    title: "Geo-Agent 服务协议",
    intro:
      '欢迎使用 Geo-Agent（以下简称"本服务"）。本协议是你与 Geo-Agent 开发团队之间关于使用本服务的法律协议。请仔细阅读以下条款。',
    sections: [
      {
        heading: "1. 服务说明",
        body: "Geo-Agent 是一个基于 AI 的地质智能问答系统，提供知识库检索、智能对话、知识库管理等功能。本服务通过检索增强生成（RAG）技术，结合用户上传的文件资料和公开网络信息，为用户提供地质学领域的专业问答。",
      },
      {
        heading: "2. 用户责任",
        body: "你同意：不利用本服务从事任何违法活动；不上传包含恶意代码、病毒或其他有害内容的文件；不尝试未经授权访问本服务的后端系统或数据库；不通过自动化脚本或爬虫大量请求本服务接口；对你上传的文件内容拥有合法权利或已获得必要授权。",
      },
      {
        heading: "3. 免责声明",
        body: "本服务提供的 AI 生成内容仅供参考，不构成专业地质学建议。对于因使用本服务提供的信息而产生的任何决策或后果，开发团队不承担法律责任。本服务可能因维护、网络故障或其他原因中断，开发团队不保证服务的持续可用性。",
      },
      {
        heading: "4. 知识产权",
        body: "Geo-Agent 系统的代码、界面设计和品牌标识归开发团队所有。用户上传的文件资料的知识产权归原作者或上传者所有。AI 生成内容的版权归属遵循相关法律法规。",
      },
      {
        heading: "5. 协议修改",
        body: "我们保留随时修改本协议的权利，修改后的协议将在本页面公布。继续使用本服务即表示你接受修改后的条款。",
      },
    ],
  },
  privacy: {
    title: "隐私说明",
    intro: "Geo-Agent 重视你的隐私。本隐私说明解释了我们如何收集、使用和保护你的个人信息。",
    sections: [
      {
        heading: "1. 信息收集",
        body: "我们收集以下信息：账号信息——注册时提供的用户名、邮箱地址和加密存储的密码；使用数据——对话记录、搜索历史、上传的文件；设备信息——浏览器类型、IP 地址、访问时间等日志数据。",
      },
      {
        heading: "2. 信息使用",
        body: "我们使用收集的信息用于：提供和改进本服务的功能；处理你的请求并生成 AI 回复；维护系统安全、排查故障；遵守法律法规的要求。我们不会将你的个人信息出售给第三方。",
      },
      {
        heading: "3. 数据存储与安全",
        body: "你的账号信息存储在加密的 MySQL 数据库中，密码使用 bcrypt 哈希存储。对话记录和文件数据保存在服务器本地。我们采取合理的技术措施保护你的数据安全，但无法保证绝对的安全。",
      },
      {
        heading: "4. Cookie 使用",
        body: "本服务使用必要的 Cookie 来维持登录状态和保存界面偏好设置（如主题模式与语言）。我们不会使用 Cookie 进行跨站追踪。",
      },
      {
        heading: "5. 数据删除",
        body: "你可以随时删除自己的对话记录和上传的文件。如需彻底删除账号及所有关联数据，请联系管理员。我们将在验证身份后的 30 个工作日内处理你的请求。",
      },
      {
        heading: "6. 第三方服务",
        body: "本服务使用第三方 AI 模型提供商（如 SiliconFlow、OpenAI 等）来处理你的请求。你在系统设置中配置的 API Key 仅存储在你的账号偏好中，不会与模型提供商以外的第三方共享。",
      },
    ],
  },
  sources: {
    title: "数据来源说明",
    intro: "Geo-Agent 的知识库数据来自多个渠道，我们致力于确保数据的准确性和合规性。",
    sections: [
      {
        heading: "1. 用户上传文件",
        body: "用户可以通过文件管理功能上传 PDF、Word、Markdown、TXT 等格式的文件资料。上传的文件经文本提取和向量化处理后存入知识库。用户应确保上传内容不侵犯第三方知识产权。",
      },
      {
        heading: "2. 公开学术资源",
        body: "系统预置知识库可能包含来自公开学术数据库（如 CNKI、万方、维普等）的文件摘要和元数据。这些内容仅用于检索增强生成，不提供全文下载。",
      },
      {
        heading: "3. 网络实时信息",
        body: "当启用网络搜索功能时，系统通过第三方搜索 API（如 Tavily）获取公开的网页信息。搜索结果仅用于增强回答的时效性，系统不会缓存或重新分发完整的网页内容。",
      },
      {
        heading: "4. AI 生成内容",
        body: "AI 生成的回答基于检索到的文件片段和网络信息，结合大语言模型的知识生成。AI 生成的内容可能包含不准确的信息，请在使用前进行核实。",
      },
      {
        heading: "5. 引用规范",
        body: "在 RAG 模式下，AI 回答会标注引用的文件来源。用户如需引用本系统提供的信息，建议追溯到原始文件进行核实，并按照学术规范引用原始出处。",
      },
    ],
  },
}

const en: Record<PolicyKey, PolicyDocument> = {
  terms: {
    title: "Geo-Agent Terms of Service",
    intro:
      'Welcome to Geo-Agent (the "Service"). These Terms constitute a legal agreement between you and the Geo-Agent development team. Please read them carefully.',
    sections: [
      {
        heading: "1. Service Description",
        body: "Geo-Agent is an AI-powered geoscience Q&A platform offering knowledge-base retrieval, conversational AI, and document management. Using retrieval-augmented generation (RAG), the Service combines your uploaded materials and publicly available web information to answer questions in geology and related fields.",
      },
      {
        heading: "2. User Responsibilities",
        body: "You agree not to use the Service for unlawful purposes; not to upload malware, viruses, or other harmful content; not to attempt unauthorized access to backend systems or databases; not to abuse the API via automated scripts or crawlers; and to ensure you have the legal right or authorization for any files you upload.",
      },
      {
        heading: "3. Disclaimer",
        body: "AI-generated content is for reference only and does not constitute professional geological advice. The development team is not liable for decisions or outcomes based on information from the Service. The Service may be interrupted for maintenance, network issues, or other reasons; continuous availability is not guaranteed.",
      },
      {
        heading: "4. Intellectual Property",
        body: "The Service's code, interface design, and branding belong to the development team. Intellectual property in user-uploaded files remains with the original authors or uploaders. Copyright in AI-generated content follows applicable laws.",
      },
      {
        heading: "5. Changes to These Terms",
        body: "We may revise these Terms at any time. Updated Terms will be published on this page. Continued use of the Service constitutes acceptance of the revised Terms.",
      },
    ],
  },
  privacy: {
    title: "Privacy Policy",
    intro: "Geo-Agent values your privacy. This policy explains how we collect, use, and protect your personal information.",
    sections: [
      {
        heading: "1. Information We Collect",
        body: "We collect: account information (username, email, and password stored in encrypted form); usage data (conversation history, search history, uploaded files); and device information (browser type, IP address, and access logs).",
      },
      {
        heading: "2. How We Use Information",
        body: "We use collected information to provide and improve the Service; process your requests and generate AI responses; maintain security and troubleshoot issues; and comply with legal requirements. We do not sell your personal information to third parties.",
      },
      {
        heading: "3. Storage and Security",
        body: "Account data is stored in an encrypted MySQL database; passwords are hashed with bcrypt. Conversations and files are stored on the server. We apply reasonable technical safeguards, but cannot guarantee absolute security.",
      },
      {
        heading: "4. Cookies",
        body: "We use essential cookies to maintain login state and UI preferences (such as theme and language). We do not use cookies for cross-site tracking.",
      },
      {
        heading: "5. Data Deletion",
        body: "You may delete your conversation history and uploaded files at any time. To fully delete your account and associated data, contact an administrator. We will process verified requests within 30 business days.",
      },
      {
        heading: "6. Third-Party Services",
        body: "The Service uses third-party AI providers (e.g., SiliconFlow, OpenAI) to process requests. API keys you configure in settings are stored in your account preferences and are not shared with parties other than the model providers.",
      },
    ],
  },
  sources: {
    title: "Data Sources",
    intro: "Geo-Agent knowledge-base data comes from multiple channels. We aim to keep data accurate and compliant.",
    sections: [
      {
        heading: "1. User-Uploaded Files",
        body: "Users may upload PDF, Word, Markdown, TXT, and other formats via document management. Files are text-extracted and vectorized for retrieval. Users must ensure uploads do not infringe third-party intellectual property.",
      },
      {
        heading: "2. Public Academic Resources",
        body: "Built-in corpora may include abstracts and metadata from public academic databases (e.g., CNKI, Wanfang, VIP). Such content is used only for RAG; full-text download is not provided.",
      },
      {
        heading: "3. Live Web Information",
        body: "When web search is enabled, the Service fetches public web content via third-party APIs (e.g., Tavily) to improve timeliness. Results are used to enhance answers; full pages are not cached or redistributed.",
      },
      {
        heading: "4. AI-Generated Content",
        body: "Answers combine retrieved passages, web snippets, and model knowledge. Generated content may be inaccurate; verify before relying on it.",
      },
      {
        heading: "5. Citation Guidelines",
        body: "In RAG mode, answers cite source documents. When citing information from this Service, trace back to original files and follow academic citation standards.",
      },
    ],
  },
}

const byLang: Record<Language, Record<PolicyKey, PolicyDocument>> = {
  "zh-CN": zhCN,
  en,
}

export function getPolicyDocument(lang: Language, key: PolicyKey): PolicyDocument {
  return byLang[lang][key]
}

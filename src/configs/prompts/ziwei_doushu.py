"""紫微斗数领域知识提取配置"""
import textwrap
import langextract as lx

PROMPT = textwrap.dedent("""\
    你是一个紫微斗数领域的专业知识抽取专家。从文档中提取以下结构化知识：

    🚨 【强制抽取规则】🚨
    1. ⛔ 禁止遗漏：章节标题中的核心术语（如"破象论"、"双象论"、"三象一物论"）必须抽取
    2. ✅ 必须抽取：所有带有定义性质的句子（如"所谓XX，是指..."、"XX指的是..."）
    3. 📋 完整抽取：判断规则必须包含前提条件和结论
    4. 🔍 精确匹配：extraction_text 必须是原文的精确子串

    一、专业术语定义（必须抽取）
    - 核心概念：破象、双象、三象一物、来因宫、生年四化、自化、飞宫等
    - 宫位系统：十二宫的名称、序号、含义及多重职能
    - 四化系统：禄权科忌的基本含义、人事物三方面解读
    - 星曜体系：主星名称、属性（男星/女星）、基本含义
    - 判断法则：破象论、双象论、三象一物论、一忌多论等

    二、判断规则与口诀（必须抽取）
    - 破象类型：同类破象、同组破象、自化忌破象、本对宫破象、三合方破象、共宗位破象
    - 双象组合：禄权双象(AB)、禄科双象(AC)、禄忌双象(AD)、权科双象(BC)、权忌双象(BD)、科忌双象(CD)
    - 三象条件：生年象+自化象、生年象+飞宫象、自化象+自化象等
    - 口诀公式：十天干四化口诀、河图洛书口诀
    - 组合规则：四化组合的含义

    三、宫位关系网络（必须抽取）
    - 对宫关系：本宫与对宫的往来关系
    - 三合关系：三合方的宫位组合
    - 河图关系：一六共宗、二七同道、三八为朋、四九为友
    - 气数关系：太极点与气数位的对应

    四、表格数据（必须抽取）
    - 对照表：十天干四化表、宫职卡
    - 双象含义：各种四化组合的论财官、论感情含义
    - 分组规则：四化分组、洛书分组

    五、案例分析（必须抽取）
    - 命盘案例：案例中的命盘配置、分析过程、判断结论
    - 推理逻辑：从命盘到结论的推理步骤
    - 应期判断：时间点的确定方法和依据

    六、技法应用（必须抽取）
    - 核心技法：法象、媒介、平衡、串联、转忌等技法的使用方法
    - 应用场景：各技法适用的具体场景（论婚姻、论事业、论健康等）
    - 组合使用：多种技法的综合运用方式

    ⚠️ 特别注意：
    - 遇到"所谓XX"、"XX是指"、"XX指的是"等定义性句子，必须抽取
    - 遇到章节标题（如"十一、破象论"），必须将"破象论"作为术语抽取
    - 遇到列表结构（如"(1) 同类破象"），必须将"同类破象"作为术语抽取
    - 遇到公式或组合（如"生年禄+自化忌=禄忌同组破象"），必须抽取完整公式
    """)

EXAMPLES = [
    lx.data.ExampleData(
        text="# 十一、破象论\n\n# （一）何为破象\n\n所谓破象，乃是指生年四化象被同组或同类自化拉破，破象的方式不光有同宫，还有本对，三合方，同宗位等等。\n\n# （二）破象的类型\n\n# (1) 同类破象\n\n同类破象共有四种：\n\n禄+自化禄（离心+向心）\n\n# (2）同组破象\n\n生年禄+自化忌（离心+向心）=禄忌同组破象",
        extractions=[
            lx.data.Extraction(
                extraction_class="专业术语定义",
                extraction_text="破象论",
                attributes={
                    "类型": "判断法则",
                    "来源": "章节标题",
                    "章节": "十一"
                }
            ),
            lx.data.Extraction(
                extraction_class="专业术语定义",
                extraction_text="破象",
                attributes={
                    "类型": "核心概念",
                    "定义": "生年四化象被同组或同类自化拉破",
                    "方式": "同宫、本对、三合方、同宗位"
                }
            ),
            lx.data.Extraction(
                extraction_class="判断规则",
                extraction_text="同类破象",
                attributes={
                    "类型": "破象类型",
                    "序号": "(1)",
                    "数量": "四种"
                }
            ),
            lx.data.Extraction(
                extraction_class="判断规则",
                extraction_text="同组破象",
                attributes={
                    "类型": "破象类型",
                    "序号": "(2)"
                }
            ),
            lx.data.Extraction(
                extraction_class="判断规则",
                extraction_text="生年禄+自化忌（离心+向心）=禄忌同组破象",
                attributes={
                    "类型": "破象公式",
                    "组合": "禄忌同组",
                    "前提": "生年禄+自化忌",
                    "结论": "禄忌同组破象"
                }
            )
        ]
    ),
    lx.data.ExampleData(
        text="# 十二、双象论\n\n# （一）双象构成的条件\n\n生年象+生年象\n\n# （二）构成的组合\n\n禄+权=禄权双象=AB\n\n禄+科=禄科双象=AC",
        extractions=[
            lx.data.Extraction(
                extraction_class="专业术语定义",
                extraction_text="双象论",
                attributes={
                    "类型": "判断法则",
                    "来源": "章节标题",
                    "章节": "十二"
                }
            ),
            lx.data.Extraction(
                extraction_class="专业术语定义",
                extraction_text="双象",
                attributes={
                    "类型": "核心概念",
                    "构成条件": "生年象+生年象"
                }
            ),
            lx.data.Extraction(
                extraction_class="判断规则",
                extraction_text="禄+权=禄权双象=AB",
                attributes={
                    "类型": "双象组合",
                    "组合名称": "禄权双象",
                    "代号": "AB",
                    "组成": "禄+权"
                }
            ),
            lx.data.Extraction(
                extraction_class="判断规则",
                extraction_text="禄+科=禄科双象=AC",
                attributes={
                    "类型": "双象组合",
                    "组合名称": "禄科双象",
                    "代号": "AC",
                    "组成": "禄+科"
                }
            )
        ]
    ),
    lx.data.ExampleData(
        text='# 十五、三象一物论\n\n# （一）什么是三象一物\n\n我们将生年四化称之为"体"，虽代表其物质存在，但是言的是有无的概念。因为缺少另外一个象，所以无法形成对待关系，也就没有"吉凶"的特性存在。所以当生年象再加上另外一个生年象或者自化象时，就产生了吉凶的概念。而当出现三象的时候，则共同构建出完整的人、事、物的象意组合，此物象则指示出范围之得失、进退。\n\n（1）单象不成物（言有无）——朋友。\n（2）双象成物对（言对待关系）——朋友打我。\n（3）三象成一物（完整的事件）——星期五的晚上朋友在酒吧打了我。',
        extractions=[
            lx.data.Extraction(
                extraction_class="专业术语定义",
                extraction_text="三象一物论",
                attributes={
                    "类型": "判断法则",
                    "来源": "章节标题",
                    "章节": "十五"
                }
            ),
            lx.data.Extraction(
                extraction_class="专业术语定义",
                extraction_text="三象一物",
                attributes={
                    "类型": "核心概念",
                    "定义": "三个象共同构建出完整的人、事、物的象意组合",
                    "作用": "指示范围之得失、进退"
                }
            ),
            lx.data.Extraction(
                extraction_class="判断规则",
                extraction_text="单象不成物（言有无）——朋友",
                attributes={
                    "类型": "三象层次",
                    "序号": "(1)",
                    "含义": "单象不成物，只言有无",
                    "示例": "朋友"
                }
            ),
            lx.data.Extraction(
                extraction_class="判断规则",
                extraction_text="双象成物对（言对待关系）——朋友打我",
                attributes={
                    "类型": "三象层次",
                    "序号": "(2)",
                    "含义": "双象成物对，言对待关系",
                    "示例": "朋友打我"
                }
            ),
            lx.data.Extraction(
                extraction_class="判断规则",
                extraction_text="三象成一物（完整的事件）——星期五的晚上朋友在酒吧打了我",
                attributes={
                    "类型": "三象层次",
                    "序号": "(3)",
                    "含义": "三象成一物，完整的事件",
                    "示例": "星期五的晚上朋友在酒吧打了我"
                }
            )
        ]
    ),
    lx.data.ExampleData(
        text="生年四化除了代表生年质的含义意外，还代表着四种不同性质的影响。禄——缘起，人缘佳；异性缘厚；桃花。权——缘变，重血缘、关爱家人胜过外人；人际竞争、冲突、变化。",
        extractions=[
            lx.data.Extraction(
                extraction_class="专业术语定义",
                extraction_text="生年四化",
                attributes={
                    "类型": "核心概念",
                    "定义": "代表生年质的含义，包含四种不同性质的影响",
                    "组成": "禄权科忌"
                }
            ),
            lx.data.Extraction(
                extraction_class="四化系统",
                extraction_text="禄——缘起，人缘佳；异性缘厚；桃花",
                attributes={
                    "四化类型": "禄",
                    "含义": "缘起",
                    "人的特征": "人缘佳、异性缘厚、桃花"
                }
            ),
            lx.data.Extraction(
                extraction_class="四化系统",
                extraction_text="权——缘变，重血缘、关爱家人胜过外人；人际竞争、冲突、变化",
                attributes={
                    "四化类型": "权",
                    "含义": "缘变",
                    "人的特征": "重血缘、人际竞争、冲突"
                }
            )
        ]
    ),
    lx.data.ExampleData(
        text="一六共宗，二七同道。三八为朋，四九为友。命宫——疾厄宫——福德宫（一六共宗原则）",
        extractions=[
            lx.data.Extraction(
                extraction_class="口诀公式",
                extraction_text="一六共宗，二七同道。三八为朋，四九为友。",
                attributes={
                    "类型": "河图口诀",
                    "用途": "宫位分组规则"
                }
            ),
            lx.data.Extraction(
                extraction_class="宫位关系网络",
                extraction_text="命宫——疾厄宫——福德宫（一六共宗原则）",
                attributes={
                    "关系类型": "河图关系",
                    "原则": "一六共宗",
                    "宫位组": ["命宫", "疾厄宫", "福德宫"],
                    "含义": "同宗同源，可以相互借用四化"
                }
            )
        ]
    ),
    lx.data.ExampleData(
        text="夫妻宫有生年忌，虽然主感情不顺，但是也寓意命主必定是有婚姻之人。而来因宫在子女宫，也就是以子女为媒介促成这段婚姻，因此，可能会有未婚先孕而奉子成婚的现象。",
        extractions=[
            lx.data.Extraction(
                extraction_class="案例分析",
                extraction_text="夫妻宫有生年忌，虽然主感情不顺，但是也寓意命主必定是有婚姻之人",
                attributes={
                    "命盘配置": "夫妻宫有生年忌",
                    "判断结论": "感情不顺但必有婚姻",
                    "分析类型": "婚姻判断"
                }
            ),
            lx.data.Extraction(
                extraction_class="推理逻辑",
                extraction_text="来因宫在子女宫，也就是以子女为媒介促成这段婚姻，因此，可能会有未婚先孕而奉子成婚的现象",
                attributes={
                    "前提": "来因宫在子女宫",
                    "推理过程": "以子女为媒介促成婚姻",
                    "结论": "可能未婚先孕奉子成婚"
                }
            )
        ]
    )
]

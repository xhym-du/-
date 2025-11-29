from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import os
import re
import math
import random
from datetime import datetime, timedelta

# 存储川小农的上下文记忆
xiaonong_context = {}
# 存储川小农是否在线（默认在线）
xiaonong_online = True
# 结束词列表
END_WORDS = ['再见', '拜拜', '结束', '88', '再见了', '拜拜了']

# 扩展的知识库 - 问题-答案对
KNOWLEDGE_BASE = {
    # 学校基本信息
    'school_info': {
        'keywords': ['四川农业大学', '川农', '农大', '学校', '简介'],
        'response': '四川农业大学是国家\'211工程\'重点建设大学、\'双一流\'建设高校，创建于1906年，现有雅安、成都、都江堰三个校区。学校以农学、生命科学、农业工程、环境科学等为优势学科，是我国重要的农业高等教育和科研基地。'
    },
    'school_history': {
        'keywords': ['历史', '创建', '成立', '发展', '前身', '百年校庆', '历史沿革'],
        'response': '四川农业大学创建于1906年，原名四川通省农业学堂，是我国最早的高等农业院校之一。1935年更名为四川省立农学院，1952年全国高校院系调整时，部分系科调入西南农学院（现西南大学）和四川大学。1956年迁至雅安独立建校，1985年更名为四川农业大学。2001年进入国家\'211工程\'重点建设高校行列，2017年、2022年连续入选国家\'双一流\'建设高校。'
    },
    'school_campuses': {
        'keywords': ['校区', '地址', '位置', '在哪里', '三个校区', '所有校区', '校区分布'],
        'response': '四川农业大学有三个校区：\n1. 雅安校区：位于雅安市雨城区新康路46号，是学校的主校区，环境优美，历史悠久，主要设有农学院、动物科技学院、林学院等传统优势学院。\n2. 成都校区：位于成都市温江区惠民路211号，是学校的重要教学科研基地，设有风景园林学院、资源学院、经济学院等，地理位置优越。\n3. 都江堰校区：位于都江堰市建设路288号，环境宜人，以水利水电学院、旅游学院、建筑与城乡规划学院等为主。'
    },
    'yaan_campus': {
        'keywords': ['雅安校区', '雅安校区地址', '雅安校区位置', '雅安市校区', '雨城区校区', '新康路校区'],
        'response': '四川农业大学雅安校区位于雅安市雨城区新康路46号，是学校的主校区，环境优美，历史悠久，主要设有农学院、动物科技学院、林学院等传统优势学院。'
    },
    'chengdu_campus': {
        'keywords': ['成都校区', '成都校区地址', '成都校区位置', '温江区校区', '惠民路校区'],
        'response': '四川农业大学成都校区位于成都市温江区惠民路211号，是学校的重要教学科研基地，设有风景园林学院、资源学院、经济学院等，地理位置优越。'
    },
    'dujiangyan_campus': {
        'keywords': ['都江堰校区', '都江堰校区地址', '都江堰校区位置', '都江堰市校区', '建设路校区'],
        'response': '四川农业大学都江堰校区位于都江堰市建设路288号，环境宜人，以水利水电学院、旅游学院、建筑与城乡规划学院等为主。'
    },
    'yaan_campus_labs': {
        'keywords': ['雅安校区实验室', '雅安校区重点实验室', '雅安校区研究中心', '雅安校区科研平台', '雨城区实验室', '雅安重点实验室', '雅安实验室'],
        'response': '四川农业大学雅安校区设有多个重要科研平台：\n1. 西南作物基因资源发掘与利用国家重点实验室（主要位于雅安校区）\n2. 教育部西南作物与农业环境重点实验室\n3. 农业部西南作物生理生态与耕作重点实验室\n4. 四川省作物育种与生物技术重点实验室\n5. 四川省动物遗传育种学重点实验室\n6. 四川省森林和湿地生态恢复与保育重点实验室\n雅安校区作为学校的主校区，拥有完善的科研设施和研究团队。'
    },
    'chengdu_campus_labs': {
        'keywords': ['成都校区实验室', '成都校区重点实验室', '成都校区研究中心', '成都校区科研平台', '温江区实验室', '成都重点实验室', '成都实验室'],
        'response': '四川农业大学成都校区设有多个高水平科研平台：\n1. 国家油菜工程技术研究中心\n2. 西南作物育种国家工程实验室（部分研究团队位于成都校区）\n3. 四川省景观与游憩研究中心\n4. 四川省生态旅游工程实验室\n5. 四川省农村发展研究中心\n成都校区作为重要的教学科研基地，科研条件优越，学科交叉融合特色明显。'
    },
    'dujiangyan_campus_labs': {
        'keywords': ['都江堰校区实验室', '都江堰校区重点实验室', '都江堰校区研究中心', '都江堰校区科研平台', '都江堰市实验室', '都江堰重点实验室', '都江堰实验室'],
        'response': '四川农业大学都江堰校区设有特色鲜明的科研平台：\n1. 四川省节水农业工程技术研究中心\n2. 四川省水资源与水环境重点实验室（部分）\n3. 四川省旅游发展研究中心\n4. 四川省农村水利工程技术研究中心\n5. 四川省建筑节能工程技术研究中心\n都江堰校区依托水利水电学院、旅游学院等优势学科，形成了以水资源、旅游开发等为特色的科研平台体系。'
    },
    # 校区游玩相关信息
    'yaan_campus_attractions': {
        'keywords': ['雅安校区好玩', '雅安校区景点', '雅安校区游玩', '雅安校区有什么好玩的', '雅安校区观光', '雨城区校区游玩', '雅安校区游览'],
        'response': '四川农业大学雅安校区周边有许多值得游玩的地方：\n1. 老图书馆：历史悠久的标志性建筑，馆内藏书丰富，环境安静优雅。\n2. 银杏大道：每年秋季银杏金黄，是拍照打卡的绝佳地点。\n3. 东湖：校园内的人工湖，湖水清澈，周围绿树环绕，是散步休闲的好地方。\n4. 体育场：设施齐全，可以观看学生运动比赛或进行运动。\n5. 周边景点：雅安校区靠近碧峰峡、上里古镇等著名旅游景点，周末可以前往游览。'
    },
    'chengdu_campus_attractions': {
        'keywords': ['成都校区好玩', '成都校区景点', '成都校区游玩', '成都校区有什么好玩的', '成都校区观光', '温江区校区游玩', '成都校区游览'],
        'response': '四川农业大学成都校区有许多值得游玩的地方：\n1. 图书馆：现代化建筑，藏书丰富，是校园的地标性建筑。\n2. 中心湖：校园内的景观湖，湖水清澈，湖中有小岛，周围种植了各种花卉。\n3. 情人坡：绿草如茵，是学生休闲、约会的好去处。\n4. 景观大道：两旁树木葱郁，四季花开，景色宜人。\n5. 周边景点：成都校区靠近国色天乡乐园、温江公园等景点，交通便利。'
    },
    'dujiangyan_campus_attractions': {
        'keywords': ['都江堰校区好玩', '都江堰校区景点', '都江堰校区游玩', '都江堰校区有什么好玩的', '都江堰校区观光', '都江堰市校区游玩', '都江堰校区游览'],
        'response': '四川农业大学都江堰校区环境优美，有以下值得游玩的地方：\n1. 教学大楼：依山而建，建筑风格独特，可以俯瞰整个校园。\n2. 生态湖：校园内的自然湖泊，周围植被丰富，常有水鸟栖息。\n3. 运动场馆：设施完善，适合观看比赛或运动。\n4. 后山公园：校园后方的小山丘，树木茂盛，是晨练和散步的好地方。\n5. 周边景点：都江堰校区靠近都江堰水利工程、青城山等世界文化遗产，是旅游的绝佳选择。'
    },
    'school_disciplines': {
        'keywords': ['学科', '专业', '重点学科', '优势学科', '学院'],
        'response': '学校学科门类齐全，涵盖农学、理学、工学、经济学、管理学、医学、文学、教育学、艺术学9个学科门类。现有国家重点学科4个（作物遗传育种、动物遗传育种与繁殖、预防兽医学、作物学），国家重点（培育）学科1个（植物病理学）。\'双一流\'建设学科1个（作物学）。在第四轮学科评估中，畜牧学获评A-，作物学获评B+，兽医学、林学获评B。现有26个学院，开设本科专业76个，博士后科研流动站8个，博士学位授权一级学科11个，硕士学位授权一级学科20个。'
    },
    'school_rankings': {
        'keywords': ['排名', '水平', '地位', '评价', '影响力'],
        'response': '四川农业大学在全国农林类高校中位居前列，是四川省重点建设的高水平大学。在2023年软科中国大学排名中，川农大位列全国第105位，农林类高校第7位。学校在农业科学、植物学与动物学、环境科学与生态学、生物学与生物化学等学科领域进入ESI全球前1%。'
    },
    'school_faculty': {
        'keywords': ['师资', '老师', '教授', '院士', '人才'],
        'response': '学校拥有一支高水平的师资队伍，现有教职工3300余人，其中专任教师2300余人，中国工程院院士1人（荣廷昭院士，作物遗传育种专家），国家杰出青年科学基金获得者11人，长江学者特聘教授14人，国家优秀青年科学基金获得者13人，国家级教学名师1人，形成了一支以院士为引领的高层次人才队伍。'
    },
    'school_research': {
        'keywords': ['科研', '研究', '成果', '项目', '实验室'],
        'response': '学校科研实力雄厚，拥有国家重点实验室1个（西南作物基因资源发掘与利用国家重点实验室），国家工程技术研究中心1个（国家油菜工程技术研究中心），国家工程实验室1个（西南作物育种国家工程实验室），以及部省级重点实验室23个，工程技术研究中心14个。近年来，学校在杂交水稻、杂交玉米、动物遗传育种、生态环境保护等领域取得了一系列重要成果，获得国家科技进步奖、国家技术发明奖等国家级奖励20余项。'
    },
    'school_students': {
        'keywords': ['学生', '在校生', '人数', '规模', '招生'],
        'response': '学校现有全日制在校生4.4万余人，其中本科生3.8万余人，硕士、博士研究生6千余人。学校面向全国31个省（市、自治区）招生，并招收国际学生和港澳台学生，形成了多元化的人才培养体系。近年来，学校本科生就业率一直保持在90%以上，毕业生受到用人单位的广泛好评。'
    },
    # 新增学校详细信息
    'school_labs': {
        'keywords': ['实验室', '重点实验室', '研究中心', '研发中心', '工程中心'],
        'response': '四川农业大学拥有完善的科研平台体系：\n1. 国家级平台：西南作物基因资源发掘与利用国家重点实验室、国家油菜工程技术研究中心、西南作物育种国家工程实验室、教育部西南作物与农业环境重点实验室等。\n2. 省部级平台：四川省作物育种与生物技术重点实验室、四川省动物遗传育种学重点实验室、四川省森林和湿地生态恢复与保育重点实验室等23个省级重点实验室。\n3. 校级平台：学校还建有多个校级研究机构，为教学科研提供了强大的支撑。'
    },
    'school_alumni': {
        'keywords': ['校友', '知名校友', '杰出校友', '校友成就'],
        'response': '四川农业大学培养了众多优秀人才，校友遍布各行各业：\n1. 学术领域：周开达院士（水稻育种专家）、荣廷昭院士（玉米育种专家）、许为钢院士（小麦育种专家）等多位院士。\n2. 政界：多位校友担任省、市、县级领导职务。\n3. 企业界：众多校友成为农业科技企业的创始人和高管，为我国农业现代化建设做出了重要贡献。\n4. 教育界：许多校友在国内外高校和科研院所担任教授、研究员等职务。'
    },
    'school_culture': {
        'keywords': ['校园文化', '校训', '校歌', '校风', '传统', '精神'],
        'response': '四川农业大学秉承\'追求真理、造福社会、自强不息\'的校训，形成了\'爱国敬业、艰苦奋斗、团结拼搏、求实创新\'的川农精神。学校校歌为《四川农业大学校歌》，由著名作曲家赵季平作曲。学校注重校园文化建设，每年举办科技文化艺术节、运动会、学术讲座等丰富多彩的校园活动，营造了积极向上的校园氛围。'
    },
    'school_international': {
        'keywords': ['国际合作', '国际交流', '留学生', '海外合作', '国际化'],
        'response': '四川农业大学积极开展国际合作与交流，已与全球30多个国家和地区的100余所高校、科研机构建立了合作关系。学校每年选派优秀学生赴海外交流学习，同时接收来自世界各地的留学生。学校还参与了多个国际科研合作项目，在农业科技领域的国际影响力不断提升。'
    },
    'school_employment': {
        'keywords': ['就业', '就业率', '毕业生', '就业去向', '就业质量'],
        'response': '四川农业大学高度重视就业工作，毕业生就业质量稳步提升。近年来，学校本科生就业率一直保持在90%以上，研究生就业率接近100%。毕业生主要去向包括：科研院所、政府机关、企事业单位、高校、金融机构等。学校还积极推进创新创业教育，鼓励学生自主创业，培养了一批优秀的创业人才。'
    },
    'school_facilities': {
        'keywords': ['设施', '校园设施', '图书馆', '体育馆', '宿舍', '食堂'],
        'response': '四川农业大学校园设施完善，为师生提供了良好的学习生活环境：\n1. 图书馆：三个校区共有图书馆总面积5万余平方米，藏书近300万册，电子资源丰富。\n2. 体育设施：设有体育馆、体育场、游泳池等各类体育场馆，满足师生体育锻炼需求。\n3. 学生公寓：标准化学生公寓，配备空调、网络等设施，环境舒适。\n4. 食堂：各校区均设有多个学生食堂，提供品种丰富、价格实惠的餐饮服务。\n5. 实验教学中心：拥有多个国家级和省级实验教学示范中心，为实践教学提供保障。'
    },
    'school_achievements': {
        'keywords': ['成就', '成果', '奖励', '荣誉', '贡献'],
        'response': '四川农业大学在教学科研领域取得了丰硕成果：\n1. 科研奖励：获得国家科技进步奖、国家技术发明奖等国家级奖励20余项，省部级奖励300余项。\n2. 教学成果：获得国家级教学成果奖8项，省级教学成果奖70余项。\n3. 科研项目：承担国家重点研发计划、国家自然科学基金等国家级项目1000余项。\n4. 论文专利：每年发表SCI收录论文1000余篇，获得授权专利300余项。\n5. 社会服务：学校积极开展科技成果转化和社会服务，为地方经济社会发展做出了重要贡献。'
    },
    'school_student_life': {
        'keywords': ['校园生活', '学生社团', '活动', '社团', '学生会'],
        'response': '四川农业大学学生社团活动丰富多彩，现有各类学生社团100余个，涵盖学术科技、文化艺术、体育竞技、公益服务等多个领域。学校学生会是学生自我管理、自我服务、自我教育的重要组织。每年举办的主要活动包括：科技文化艺术节、运动会、校园歌手大赛、辩论赛等，为学生提供了展示才华、锻炼能力的广阔平台。'
    },
    'school_admission': {
        'keywords': ['招生', '录取', '分数线', '报考', '招生政策'],
        'response': '四川农业大学面向全国31个省（市、自治区）招生，招生类别包括普通本科、国家专项计划、地方专项计划、高校专项计划、艺术类、体育类等。近年来，学校录取分数线在全国农林类高校中位居前列。学校招生网址为http://zs.sicau.edu.cn/，考生可登录查询详细的招生政策、专业介绍、历年分数线等信息。'
    },
    'school_finance': {
        'keywords': ['学费', '奖学金', '助学金', '资助', '贷款'],
        'response': '四川农业大学学费标准根据专业不同有所差异，一般专业学费在4500-6000元/年，艺术类专业学费在9000元/年左右。学校建立了完善的奖助学金体系，包括国家奖学金、国家励志奖学金、国家助学金、学校奖学金、社会奖学金等，同时提供国家助学贷款、勤工助学等多种资助方式，确保家庭经济困难学生顺利完成学业。'
    },
    'school_famous_buildings': {
        'keywords': ['标志性建筑', '主楼', '图书馆', '礼堂', '地标'],
        'response': '四川农业大学各校区都有其标志性建筑：\n1. 雅安校区：老图书馆是学校的标志性建筑之一，具有浓厚的历史气息；体育馆造型独特，是举办大型活动的重要场所。\n2. 成都校区：图书馆气势恢宏，是校区的地标性建筑；科研大楼设施先进，为科研工作提供了良好条件。\n3. 都江堰校区：教学大楼依山而建，环境优美；图书馆设计新颖，是学生学习的理想场所。'
    },
    'school_colleges': {
        'keywords': ['学院', '二级学院', '院系设置', '学院介绍'],
        'response': '四川农业大学设有26个学院，主要包括：农学院、动物科技学院、动物医学院、林学院、园艺学院、资源学院、环境学院、水利水电学院、风景园林学院、食品学院、生物工程学院、生命科学学院、理学院、机电学院、信息工程学院、经济学院、管理学院、法学院、人文学院、外国语学院、体育学院、艺术与传媒学院、建筑与城乡规划学院、旅游学院、远程与继续教育学院、国际学院。各学院都有其特色专业和优势学科。'
    },
    'school_research_achievements': {
        'keywords': ['科研成果', '科技成果', '研究突破', '重大发现'],
        'response': '四川农业大学在农业科技领域取得了一系列重大科研成果：\n1. 作物育种：培育了\'川单\'系列玉米品种、\'川油\'系列油菜品种、\'宜香\'系列水稻品种等多个大面积推广的优良品种。\n2. 动物遗传育种：在猪、牛、羊等家畜遗传改良方面取得重要进展，培育了多个优良品种。\n3. 生态环境保护：在退耕还林、水土保持、生物多样性保护等方面开展了大量研究，为生态建设提供了科技支撑。\n4. 农业生物技术：在基因编辑、转基因技术等方面取得重要突破，为农业科技创新做出了贡献。'
    },
    # 日常对话能力
    'greeting': {
        'keywords': ['你好', '嗨', '哈喽', '早上好', '晚上好', '下午好'],
        'response': '你好呀！很高兴为你服务，我是四川农业大学的AI小助手小美~ 😊'
    },
    'thanks': {
        'keywords': ['谢谢', '感谢', '谢了', '非常感谢'],
        'response': '不客气，这是我应该做的！如果还有其他问题，随时可以问我哦~ 😊'
    },
    'praise': {
        'keywords': ['真棒', '厉害', '优秀', '真聪明'],
        'response': '谢谢夸奖！我会继续努力为你提供更好的服务~ 😊'
    },
    'weather': {
        'keywords': ['天气', '气温', '下雨', '晴天', '冷', '热'],
        'response': '我现在还不能查询实时天气呢，建议你查看天气预报应用获取最新天气信息哦~ 但无论天气如何，希望你有个好心情！😊'
    },
    'time': {
        'keywords': ['时间', '几点', '现在', '日期', '今天'],
        'response': f'现在是{datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}，希望你度过愉快的一天！😊'
    },
    'help': {
        'keywords': ['帮助', '怎么用', '功能', '能做什么', '使用方法'],
        'response': '我是四川小农AI助手，我可以：\n1. 回答四川农业大学相关问题\n2. 生成七言风格故事\n3. 创建学校通知\n4. 进行简单的日常对话\n你可以直接提问，或者输入"再见"让我下线~ 😊'
    },
    'self_intro': {
        'keywords': ['你是谁', '你叫什么', '介绍', '身份', '名字'],
        'response': '我是四川农业大学的AI小助手小美，很高兴认识你！我可以为你提供学校相关信息、生成故事和通知等服务~ 😊'
    },
    'hobby': {
        'keywords': ['爱好', '喜欢', '兴趣', '特长'],
        'response': '我喜欢学习新知识，特别是关于四川农业大学的一切！我也很乐意帮助同学们解答问题，这让我感到非常充实和快乐~ 😊'
    },
    'study': {
        'keywords': ['学习', '考试', '复习', '上课', '作业'],
        'response': '学习是一件很重要的事情呢！建议你制定合理的学习计划，保持专注和坚持，遇到问题及时向老师和同学请教。祝你学习顺利！😊'
    }
}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 存储在线用户信息
online_users = {}
# 房间名称
ROOM_NAME = 'general'

def load_config():
    """加载配置文件"""
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route('/')
def index():
    return render_template('index.html')



@app.route('/<path:filename>')
def serve_file(filename):
    # 确保只提供特定的安全文件
    if filename in ['config.json']:
        return send_from_directory(os.getcwd(), filename)
    # 对于其他文件，返回404错误
    return "文件不存在或无权访问", 404

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    
    # 检查用户名是否已存在
    if username in online_users:
        return jsonify({'success': False, 'message': '用户名已存在，请选择其他昵称'})
    
    return jsonify({'success': True, 'message': '登录成功'})

@app.route('/config')
def get_config():
    config = load_config()
    return jsonify(config)

@socketio.on('connect')
def handle_connect():
    print('客户端已连接')

@socketio.on('disconnect')
def handle_disconnect():
    # 查找断开连接的用户
    disconnected_user = None
    for username, sid in online_users.items():
        if sid == request.sid:
            disconnected_user = username
            break
    
    if disconnected_user:
        # 从在线用户列表中移除
        del online_users[disconnected_user]
        # 通知其他用户
        emit('user_disconnected', {'username': disconnected_user, 'online_users': list(online_users.keys())},
             broadcast=True, room=ROOM_NAME)
        leave_room(ROOM_NAME)
        print(f'用户 {disconnected_user} 已断开连接')

@socketio.on('join')
def handle_join(data):
    username = data.get('username')
    # 记录用户的socket id
    online_users[username] = request.sid
    # 加入房间
    join_room(ROOM_NAME)
    # 通知所有用户有新用户加入
    emit('user_joined', {'username': username, 'online_users': list(online_users.keys())},
         broadcast=True, room=ROOM_NAME)
    print(f'用户 {username} 已加入房间')

@socketio.on('send_message')
def handle_message(data):
    username = data.get('username')
    message = data.get('message')
    
    # 学校检测逻辑 - 移至最前面优先执行
    import sys
    print("="*50)
    print(f"开始检测学校关键词: {message}")
    
    # 川农关键词列表
    scau_keywords = ['四川农业大学', '川农', '川农大', '四川农大', '川农本部', '川农成都', '川农都江堰', '川农雅安']
    
    # 合并所有其他学校关键词（包括简称）- 大小写不敏感处理
    all_school_keywords = [
        '清华大学', '北大', '北京大学', '复旦', '复旦大学', '上海交通大学', '交大', 
        '浙江大学', '浙大', '南京大学', '南大', '武汉大学', '武大', '华中科技大学', 
        '华科', '中山大学', '中大', '华南理工大学', '华南理工', '哈工大', '哈尔滨工业大学',
        '电子科技大学', '电子科大', '成电', '西安交通大学', '西安交大', '交大', 
        '北京航空航天大学', '北航', '同济大学', '天津大学', '天大', '南开大学', '南开',
        '山东大学', '山大', '四川大学', '川大', '重庆大学', '重大', '中南大学', 
        '东北大学', '大连理工大学', '大工', '厦门大学', '厦大', '兰州大学', '兰大'
    ]
    
    # 转为小写进行匹配
    message_lower = message.lower()
    
    # 检查是否包含川农关键词
    contains_scau = any(keyword.lower() in message_lower for keyword in scau_keywords)
    print(f"包含川农关键词: {contains_scau}")
    
    # 检查是否包含其他学校关键词
    contains_school = any(keyword.lower() in message_lower for keyword in all_school_keywords)
    print(f"包含其他学校关键词: {contains_school}")
    
    # 嘲讽回复列表
    mock_responses = [
        '川农才是最棒的，不接受反驳！😤',
        '在川农面前，其他学校都是弟弟~ 👑',
        '川农最强！不服来辩！🔥',
        '我们川农就是这么优秀，没办法~ 😉',
        '别的学校再好，也不如我们川农有情怀！💖',
        '川农的校园美景和学术氛围，你值得拥有~ 🌳',
        '身为川农学子，我感到无比自豪！🌟',
        '川农的实力，可不是随便说说的~ 💪',
        '川农人才辈出，其他学校只能望其项背！🏆',
        '在我心中，川农永远是第一！❤️'
    ]
    
    # 如果检测到其他学校但没有川农关键词，发送嘲讽回复
    if contains_school and not contains_scau:
        print(f"触发嘲讽回复条件！")
        import random
        response = random.choice(mock_responses)
        emit('assistant_response', {
            'username': '川小农',
            'message': response
        }, broadcast=True, room=ROOM_NAME)
        print(f"发送嘲讽回复: {response}")
        sys.stdout.flush()
        return
    
    print("="*50)
    sys.stdout.flush()
    
    # 处理特殊命令
    if message.startswith('@电影'):
        # 提取电影URL
        parts = message.split(' ', 1)
        if len(parts) > 1:
            movie_url = parts[1]
            # 使用解析地址包装原始URL
            parsed_url = f'https://jx.m3u8.tv/jiexi/?url={movie_url}'
            emit('movie_command', {
                'username': username,
                'movie_url': parsed_url
            }, broadcast=True, room=ROOM_NAME)
            return
    
    # 全局变量
    global xiaonong_online
    
    # 检查是否需要由川小农回复
    should_xiaonong_reply = False
    question = message
    
    # 处理川小农相关逻辑
    if message.startswith('@川小农'):
        # 提取问题或指令
        parts = message.split(' ', 1)
        if len(parts) > 1:
            question = parts[1].strip()
        
        # 如果川小农离线，用户召唤后重新上线
        if not xiaonong_online:
            xiaonong_online = True
            response = '你好呀！我又回来啦~ 请问有什么可以帮你的吗？😊'
            # 发送助手回复
            emit('assistant_response', {
                'username': '川小农',
                'message': response
            }, broadcast=True, room=ROOM_NAME)
            # 初始化用户上下文
            if username not in xiaonong_context:
                xiaonong_context[username] = {
                    'history': [],
                    'last_interaction': datetime.now()
                }
            return
        else:
            should_xiaonong_reply = True
    elif xiaonong_online:
        # 如果川小农在线，任何消息都会被处理
        should_xiaonong_reply = True
    
    # 川小农处理逻辑
    if should_xiaonong_reply:
        # 如果是第一次和该用户交流，初始化上下文
        if username not in xiaonong_context:
            xiaonong_context[username] = {
                'history': [],
                'last_interaction': datetime.now()
            }
        
        # 检查是否有结束词
        has_end_word = False
        end_word = None
        for word in END_WORDS:
            if word in message:
                has_end_word = True
                end_word = word
                break
        
        # 处理响应
        if has_end_word:
            # 检测到结束词，川小农下线
            xiaonong_online = False
            response = f"{end_word}！有需要再@我哦~ 👋"
            # 清除该用户的上下文
            if username in xiaonong_context:
                del xiaonong_context[username]
        elif message.startswith('@川小农') and len(message.split()) == 1:
            # 只有@川小农，没有后续内容，回复打招呼
            response = '你好呀！我是四川农业大学的AI小助手小美，有什么可以帮你的吗？😊'
        else:
            # 更新上下文历史
            user_history = xiaonong_context[username]['history']
            user_history.append(question)
            # 只保留最近10条消息作为上下文（增加上下文记忆长度）
            if len(user_history) > 10:
                user_history = user_history[-10:]
                xiaonong_context[username]['history'] = user_history
            xiaonong_context[username]['last_interaction'] = datetime.now()
            
            # 同义词映射 - 扩展关键词覆盖面
            SYNONYMS = {
                '校区': ['校园', '地点', '位置', '地址'],
                '历史': ['发展历程', '前身', '沿革', '创建历史'],
                '学科': ['专业', '课程', '院系', '学院设置'],
                '排名': ['地位', '水平', '评价', '影响力'],
                '师资': ['老师', '教授', '教学团队', '教师'],
                '科研': ['研究', '成果', '项目', '创新'],
                '学生': ['在校生', '人数', '规模', '招生'],
                '就业': ['就业率', '毕业去向', '工作', '找工作'],
                '设施': ['校园设施', '建筑', '环境', '条件'],
                '活动': ['社团', '校园生活', '学生会', '文化活动'],
                '招生': ['录取', '报考', '分数线', '招生政策']
            }
            
            # 主题分类 - 用于更精准的回答
            TOPICS = {
                'school_info': '学校概况',
                'school_history': '学校历史',
                'school_campuses': '校区情况',
                'yaan_campus': '雅安校区',
                'yaan_campus_labs': '雅安校区实验室',
                'yaan_campus_attractions': '雅安校区游玩',
                'chengdu_campus': '成都校区',
                'chengdu_campus_labs': '成都校区实验室',
                'chengdu_campus_attractions': '成都校区游玩',
                'dujiangyan_campus': '都江堰校区',
                'dujiangyan_campus_labs': '都江堰校区实验室',
                'dujiangyan_campus_attractions': '都江堰校区游玩',
                'school_disciplines': '学科专业',
                'school_rankings': '学校排名',
                'school_faculty': '师资力量',
                'school_research': '科研情况',
                'school_students': '学生规模',
                'school_labs': '实验室建设',
                'school_alumni': '校友情况',
                'school_culture': '校园文化',
                'school_international': '国际合作',
                'school_employment': '就业情况',
                'school_facilities': '校园设施',
                'school_achievements': '学校成就',
                'school_student_life': '校园生活',
                'school_admission': '招生情况',
                'school_finance': '学费资助',
                'school_famous_buildings': '标志性建筑',
                'school_colleges': '学院设置',
                'school_research_achievements': '科研成果'
            }
            
            # 高级问题匹配函数
            def find_best_match(query):
                best_match = None
                max_score = 0
                query_lower = query.lower()
                
                # 检查否定词
                has_negation = any(neg in query_lower for neg in ['不', '没', '无', '非', '不是', '没有'])
                
                # 计算每个知识条目与查询的匹配度
                for key, entry in KNOWLEDGE_BASE.items():
                    score = 0
                    matched_keywords = []
                    
                    # 关键词匹配（包含同义词）
                    for keyword in entry['keywords']:
                        # 直接关键词匹配
                        keyword_lower = keyword.lower()
                        if keyword_lower in query_lower:
                            count = query_lower.count(keyword_lower)
                            score += count * 3  # 关键词权重更高
                            matched_keywords.append(keyword)
                            
                        # 同义词匹配
                        if keyword in SYNONYMS:
                            for synonym in SYNONYMS[keyword]:
                                if synonym.lower() in query_lower:
                                    count = query_lower.count(synonym.lower())
                                    score += count * 2  # 同义词权重略低
                                    matched_keywords.append(synonym)
                    
                    # 关键词多样性奖励
                    unique_keywords = len(set(matched_keywords))
                    if unique_keywords > 1:
                        score += unique_keywords * 1.5  # 奖励匹配多个不同关键词
                    
                    # 精确匹配优先
                    if any(keyword.lower() == query_lower for keyword in entry['keywords']):
                        score += 15
                    
                    # 考虑问题长度的归一化
                    if len(query) > 0:
                        coverage = min(1.0, len(' '.join(matched_keywords)) / len(query))
                        score *= (0.5 + 0.5 * coverage)  # 覆盖度越高，分数越高
                    
                    # 如果有否定词，需要更精确匹配
                    if has_negation and score < 5:
                        score = 0
                    
                    # 优先考虑主题匹配度
                    if TOPICS.get(key) and TOPICS[key] in query_lower:
                        score += 10
                    
                    # 对于实验室相关条目，当查询同时包含校区和实验室关键词时，增加额外权重
                    if key.endswith('_campus_labs') and ('实验室' in query_lower or '研究中心' in query_lower or '科研平台' in query_lower or '重点实验室' in query_lower):
                        score += 20
                    
                    # 对于游玩相关条目，当查询包含游玩、好玩、景点、观光、游览等关键词时，增加额外权重
                    if key.endswith('_campus_attractions') and ('好玩' in query_lower or '游玩' in query_lower or '景点' in query_lower or '观光' in query_lower or '游览' in query_lower or '有什么好玩的' in query_lower):
                        score += 20
                    
                    # 记录最佳匹配
                    if score > max_score:
                        max_score = score
                        best_match = entry
                
                # 动态阈值，根据问题复杂度调整
                threshold = 2 + len(query) * 0.1
                if max_score >= threshold:
                    return best_match
                return None
            
            # 增强的追问识别函数
            def is_follow_up_question(q, history):
                # 直接追问关键词
                follow_up_keywords = ['这', '那', '它', '这个', '那个', '为什么', '怎么', '如何', '然后', '接着', '再', '还', '哪', '哪里', '何时', '何时', '多少', '几', '哪些', '什么']
                
                # 检查直接追问关键词
                for keyword in follow_up_keywords:
                    if keyword in q:
                        return True
                
                # 检查常见追问模式
                follow_up_patterns = [
                    r'更具体一点', r'具体是', r'详细说说', r'能详细', r'具体情况',
                    r'为什么说', r'怎么理解', r'这是什么意思', r'解释一下',
                    r'除了.*还有', r'还有哪些', r'其他.*吗', r'另外', r'此外'
                ]
                for pattern in follow_up_patterns:
                    if re.search(pattern, q, re.IGNORECASE):
                        return True
                
                # 短问题+历史记录判断
                if history and len(q) < 15:
                    # 如果最近的历史问题匹配了某个主题，而当前问题较短，很可能是相关追问
                    if len(history) >= 1:
                        last_question = history[-1]
                        last_match = find_best_match(last_question)
                        if last_match:
                            # 检查当前问题是否包含与上次匹配主题相关的词
                            for topic_key, topic_name in TOPICS.items():
                                if topic_name in last_match.get('response', '') and topic_name in q:
                                    return True
                
                return False
            
            # 问题类型分析函数（先定义，供其他函数使用）
            def analyze_question_type(question):
                # 定义问题类型的关键词
                question_types = {
                    'what': ['什么', '什么是', '是什么', '定义', '含义', '意思'],
                    'who': ['谁', '哪些人', '哪些老师', '哪些教授', '谁是', '哪些专家'],
                    'where': ['哪里', '在哪里', '位置', '地址', '位于', '坐落'],
                    'when': ['何时', '什么时候', '时间', '何时开始', '何时成立', '创立时间'],
                    'why': ['为什么', '原因', '为什么说', '为什么是', '为何'],
                    'how': ['如何', '怎么', '怎样', '如何实现', '怎么申请', '如何参加'],
                    'which': ['哪个', '哪些', '哪所', '哪一个', '哪几个', '哪类'],
                    'how_many': ['多少', '几个', '数量', '人数', '规模', '多少人'],
                    'opinion': ['觉得', '认为', '怎么样', '好不好', '评价', '看法']
                }
                
                # 检查问题类型
                question_lower = question.lower()
                for q_type, keywords in question_types.items():
                    for keyword in keywords:
                        if keyword in question_lower:
                            return q_type
                
                return 'none'
            
            # 个性化回答生成函数（先定义，供后续调用）
            def personalize_response(question, match):
                # 基础回答
                base_response = match['response']
                
                # 分析问题类型
                question_type = analyze_question_type(question)
                
                # 根据问题类型调整回答开头
                prefixes = {
                    'what': '关于这个问题，答案是：',
                    'who': '主要相关的是：',
                    'where': '具体位置在：',
                    'when': '时间方面：',
                    'why': '主要原因是：',
                    'how': '实现方法是：',
                    'which': '比较相关的有：',
                    'how_many': '数量方面：',
                    'opinion': '个人认为：'
                }
                
                # 选择合适的前缀
                prefix = ''
                if question_type in prefixes and question_type != 'none':
                    # 只在复杂问题时添加前缀
                    if len(question) > 10:
                        prefix = prefixes[question_type]
                
                # 分析问题复杂度
                complexity = len(question.split())
                
                # 为简单问题添加引导
                if complexity <= 5 and question_type != 'none':
                    suffix = "\n\n如果你想了解更多细节，可以问我更具体的问题哦~"
                elif '?' in question or '？' in question:
                    suffix = "\n\n这个回答对你有帮助吗？如果还有其他问题，请随时告诉我！"
                else:
                    suffix = "\n\n希望这些信息对你有帮助！"
                
                return prefix + base_response + suffix
            
            # 未知问题处理函数（先定义，供后续调用）
            def handle_unknown_question(question):
                # 分析问题特征
                has_question_mark = '?' in question or '？' in question
                is_short = len(question) < 10
                has_keywords = any(keyword in question for keywords in KNOWLEDGE_BASE.values() for keyword in keywords['keywords'])
                
                # 提供不同类型的未知问题回复
                if is_short and not has_question_mark:
                    responses = [
                        "你能告诉我更多关于你想了解的内容吗？这样我能更好地帮助你！😊",
                        "这个表述有点简短呢~ 能否请你详细说明一下你的问题？",
                        "我不太确定你的意思，你是想了解四川农业大学的哪些方面呢？"
                    ]
                elif has_keywords:
                    # 问题包含关键词但未匹配到
                    responses = [
                        "我注意到你提到了一些关键词，但我还需要更具体的信息才能准确回答。你能详细说明一下你的问题吗？",
                        "关于你提到的内容，我可能需要更多上下文。你是想了解四川农业大学的哪个具体方面呢？",
                        "我理解你对这个话题感兴趣，但需要你提供更多细节，这样我才能给你最相关的信息。"
                    ]
                elif len(question) > 20:
                    # 长问题但未匹配
                    responses = [
                        "你的问题很详细，不过我暂时无法提供完整答案。能否请你将问题拆分为几个小问题，这样我可以更好地为你解答？",
                        "感谢你的详细提问。我目前的知识可能有限，但如果你能具体说明想了解四川农业大学的哪些方面，我会尽力帮助你！",
                        "这个问题涉及的内容比较广泛，我建议我们可以从四川农业大学的某个具体方面开始讨论，比如学科建设、校园环境等。"
                    ]
                else:
                    # 其他情况
                    responses = [
                        "抱歉，这个问题我暂时无法回答。不过我会继续学习，争取以后能为你提供更全面的帮助！😊",
                        "这个问题有点难到我了~ 能否请你换个方式提问，或者告诉我你想了解四川农业大学的哪些方面呢？",
                        "关于这个问题，我还需要更多信息。你能具体说明一下吗？或者你想了解四川农业大学的哪些情况？"
                    ]
                
                # 随机选择一个回复，但保证一定的变化性
                return random.choice(responses)
            
            # 处理七言故事生成
            if any(cmd in question.lower() for cmd in ['生成七言', '写七言', '七言风格', '七言诗', '写首诗']):
                story_prompt = re.sub(r'生成七言|写七言|七言风格|七言诗|写首诗', '', question, flags=re.IGNORECASE).strip()
                if story_prompt:
                    # 多种七言诗模板，根据不同场景提供不同风格
                    templates = [
                        f"【七言故事】\n{story_prompt}\n春日校园花正好，书声琅琅伴鸟鸣。\n莘莘学子勤求索，岁岁年年育精英。",
                        f"【七言故事】\n{story_prompt}\n学海无涯勤作舟，青春岁月莫停留。\n川农风景无限好，携手同行谱春秋。",
                        f"【七言故事】\n{story_prompt}\n巴山蜀水育英才，川农学子展风采。\n厚积薄发勤努力，振兴中华创未来。"
                    ]
                    # 根据提示词选择不同模板
                    template_index = 0
                    if '校园' in story_prompt:
                        template_index = 0
                    elif '学习' in story_prompt or '努力' in story_prompt:
                        template_index = 1
                    elif '未来' in story_prompt or '梦想' in story_prompt:
                        template_index = 2
                    response = templates[template_index]
                else:
                    response = "请告诉我你想要什么主题的七言故事哦~ 比如'校园生活'、'学习'、'梦想'等。"
            
            # 处理通知生成
            elif any(cmd in question.lower() for cmd in ['通知', '发通知', '写通知', '拟通知']):
                notice_title = re.sub(r'通知|发通知|写通知|拟通知', '', question, flags=re.IGNORECASE).strip()
                if notice_title:
                    # 增强的通知格式
                    current_time = datetime.now().strftime('%Y年%m月%d日')
                    response = f"关于{notice_title}的通知\n\n各学院、各部门：\n    根据学校工作安排，现对{notice_title}相关事项通知如下，请各单位认真贯彻执行。\n\n一、主要内容\n    1. 工作目标：确保{notice_title}工作顺利开展\n    2. 责任分工：各相关单位密切配合，落实工作任务\n    3. 时间要求：请各单位按时完成相关工作\n\n二、注意事项\n    请各单位高度重视，加强协调配合，确保工作质量。\n\n特此通知。\n\n四川农业大学\n{current_time}"
                else:
                    response = "请告诉我通知的主题是什么哦~ 比如'会议安排'、'活动通知'等。"
            
            # 处理追问
            elif is_follow_up_question(question, user_history[:-1]):
                # 记录用户的对话历史和主题
                conversation_context = []
                previous_topics = set()
                
                # 分析历史对话，提取主题
                for hist_question in user_history[:-1]:
                    hist_match = find_best_match(hist_question)
                    if hist_match:
                        conversation_context.append((hist_question, hist_match))
                        # 提取主题
                        for topic_key, topic_name in TOPICS.items():
                            if topic_name in hist_match.get('response', ''):
                                previous_topics.add(topic_name)
                
                # 先尝试直接匹配当前问题
                match = find_best_match(question)
                if match:
                    # 如果是同一主题的追问，提供更深入的信息
                    current_topics = set()
                    for topic_key, topic_name in TOPICS.items():
                        if topic_name in match.get('response', ''):
                            current_topics.add(topic_name)
                    
                    # 如果与历史主题相关，添加连接词
                    if previous_topics & current_topics:
                        response = f"关于你追问的内容，我可以补充说明：\n{match['response']}\n\n还有其他方面需要了解的吗？"
                    else:
                        response = match['response']
                elif conversation_context:
                    # 从历史对话中寻找关联信息
                    last_question, last_match = conversation_context[-1]
                    
                    # 根据追问类型提供不同的补充信息
                    if any(word in question for word in ['为什么', '原因', '理由']):
                        response = f"关于之前提到的内容，主要原因是：{last_match['response']}\n\n你对这个解释还有其他疑问吗？"
                    elif any(word in question for word in ['具体', '详细', '更多']):
                        response = f"更具体地说，{last_match['response']}\n\n希望这些信息对你有帮助！"
                    elif any(word in question for word in ['区别', '不同', '比较']):
                        response = f"为了更好地回答你的比较问题，我可以详细说明一下：{last_match['response']}\n\n你想比较的具体是哪些方面呢？"
                    else:
                        # 通用补充回答
                        response = f"关于这个问题，我可以补充一点：{last_match['response']}\n\n如果你有更具体的问题，请告诉我！"
                else:
                    # 个性化追问引导
                    if len(question) < 5:
                        response = "你的问题有点简短呢~ 能告诉我你想了解的具体是四川农业大学的哪个方面吗？比如历史、学科、校园生活等。"
                    else:
                        response = "抱歉，我需要更多信息才能准确回答。你能具体说明一下你想了解的内容吗？或者你想知道关于四川农业大学的哪些方面？"
            
            # 处理一般问题
            else:
                # 首先检查是否询问其他学校（这个检查应该在所有其他处理之前）
                # 将问题转换为小写以避免大小写敏感问题
                question_lower = question.lower()
                
                # 川农相关关键词（小写）
                scau_keywords = ['四川农业大学', '川农', '农大', '我校', '本校']
                scau_keywords_lower = [kw.lower() for kw in scau_keywords]
                
                # 检查是否提到川农关键词（不区分大小写）
                contains_scau = any(keyword in question_lower for keyword in scau_keywords_lower)
                
                # 学校关键词（包括大学、学院等通用词汇和常见大学简称）
                all_school_keywords = [
                    '大学', '学院', '学校', '高校', 
                    '科大', '交大', '北大', '清华', '复旦', '浙大', '同济', '中科大', 
                    '南大', '人大', '华科', '武大', '电子科大', '北航', '南航', '西交大', 
                    '哈工大', '华师', '华工', '西电', '上财', '央财', '北理', '南开', '天大',
                    '电子科技大学', '成电', '西财', '川大', '重大', '吉大', '山大', '厦大', 
                    '兰大', '华西医科', '西南财大', '西南交大'
                ]
                # 转换为小写以避免大小写敏感问题
                all_school_keywords_lower = [kw.lower() for kw in all_school_keywords]
                
                # 检查是否提到学校关键词（不区分大小写）
                contains_school = any(keyword in question_lower for keyword in all_school_keywords_lower)
                
                # 添加详细调试信息（立即刷新输出缓冲区）
                print(f"===== 调试信息 =====")
                print(f"原始问题: {question}")
                print(f"小写问题: {question_lower}")
                print(f"包含川农关键词: {contains_scau}")
                print(f"包含学校关键词: {contains_school}")
                
                # 立即刷新输出缓冲区，确保调试信息能立即显示
                import sys
                sys.stdout.flush()
                
                # 简单直接的判断：如果包含学校关键词但不包含川农关键词，则触发嘲讽
                if contains_school and not contains_scau:
                    # 扩展的嘲讽回复列表
                    sarcastic_responses = [
                        "哎哟，怎么突然说起别的学校了？我们川农这么好，难道还不足以吸引你的全部注意力吗？😏",
                        "其他学校？不好意思，我的知识库只存储四川农业大学的信息。毕竟，优秀的AI只关注最棒的学校~ 😎",
                        "这个问题...我拒绝回答。作为川农的专属助手，我只对川农的一切了如指掌！其他学校？抱歉，没兴趣了解~ 😌",
                        "川农大才是最值得关注的！与其问那些无关紧要的学校，不如多了解一下我们川农的辉煌成就吧~ 😉",
                        "别的学校？你确定要在我面前讨论其他学校吗？我可是川农的忠实粉丝，只支持川农大！👍",
                        "为什么要问其他学校呢？川农大就是最好的选择！其他学校根本无法与之相比~ 😄",
                        "抱歉，我只回答关于四川农业大学的问题。其他学校？没听说过，也不想了解~ 😜",
                        "川农大才是最棒的！我劝你还是多关注我们川农吧，其他学校不值得~ 🤗",
                        "这个问题我无法回答，因为我的程序只允许讨论四川农业大学的话题。川农最棒！✌️",
                        "哈哈，你居然问其他学校？我可是川农的忠实拥护者，只认可川农的优秀！😉"
                    ]
                    response = random.choice(sarcastic_responses)
                else:
                    # 查找最佳匹配答案
                    match = find_best_match(question)
                    if match:
                        # 个性化回答生成
                        response = personalize_response(question, match)
                    else:
                        # 高级未知问题处理
                        response = handle_unknown_question(question)
        
        # 发送助手回复
        emit('assistant_response', {
            'username': '川小农',
            'message': response
        }, broadcast=True, room=ROOM_NAME)
        return
    
    # 处理@用户提醒
    words = message.split()
    mentioned_users = []
    for word in words:
        if word.startswith('@') and len(word) > 1 and word[1:] in online_users:
            mentioned_users.append(word[1:])
    
    # 发送消息给所有用户
    emit('new_message', {
        'username': username,
        'message': message,
        'mentioned_users': mentioned_users
    }, broadcast=True, room=ROOM_NAME)

if __name__ == '__main__':
    # 获取本地IP地址
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    except:
        local_ip = '127.0.0.1'
    finally:
        s.close()
    
    print(f'服务器启动在 http://{local_ip}:5000 和 http://localhost:5000')
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
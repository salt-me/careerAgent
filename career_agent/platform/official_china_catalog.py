"""Review queue for Chinese employer-owned careers pages.

Entries are deliberately separate from active connectors.  A source is made
active only after its public page/ATS contract is tested and its absence
semantics are understood; otherwise a failed request could incorrectly archive
real jobs.  This makes expansion auditable rather than a fragile scraper list.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class OfficialChinaSource:
    company: str
    career_url: str
    integration_status: str
    lifecycle_mode: str
    next_validation: str
    trust_basis: str = "employer_owned_official_domain"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


OFFICIAL_CHINA_SOURCE_CATALOG = (
    OfficialChinaSource("百度", "https://talent.baidu.com/jobs/list?projectType=1", "active_public_ssr", "non_authoritative", "校验 SSR 字段与届别页面"),
    OfficialChinaSource("华为", "https://career.huawei.com/cn", "official_public_board_review_pending", "disabled", "确认公开职位搜索的分页、稳定职位 ID 与关闭语义"),
    OfficialChinaSource("OPPO", "https://careers.oppo.com/university/oppo/campus/post", "official_public_board_review_pending", "disabled", "确认校招页面恢复岗位后可公开读取的列表字段与分页"),
    OfficialChinaSource("Bambu Lab", "https://bambulab.jobs.feishu.cn/campus", "official_feishu_board_review_pending", "disabled", "从公开岗位列表定位稳定职位 ID；不使用带分享令牌的投递记录链接"),
    OfficialChinaSource("拼多多集团", "https://careers.pddglobalhr.com/campus/grad", "active_public_api", "non_authoritative", "已验证公开分页岗位列表；确认职位下架是否始终代表关闭后再启用归档"),
    OfficialChinaSource("DJI 大疆", "https://apply.careers.dji.com/social-recruitment/dji/170070?hash=%23%2Fjobs", "official_public_board_review_pending", "disabled", "确认公开岗位列表的校招、实习和社招范围；不使用个人投递查询页"),
    OfficialChinaSource("智元机器人", "https://agirobot.jobs.feishu.cn/campusrecruitment", "official_feishu_board_review_pending", "disabled", "从公开岗位列表定位稳定职位 ID；不使用带分享令牌的投递记录链接"),
    OfficialChinaSource("普渡科技", "https://pudutech1.zhiye.com/", "official_public_board_review_pending", "disabled", "确认公开岗位列表和详情页；不使用个人投递记录链接"),
    OfficialChinaSource("科大讯飞", "https://iflytek.zhiye.com/", "official_public_board_review_pending", "disabled", "确认公开岗位列表和详情页；不使用个人投递记录链接"),
    OfficialChinaSource("Ubiquant", "https://app.mokahr.com/campus_apply/ubiquantrecruit/37031", "official_public_board_review_pending", "disabled", "确认公开校招列表的分页与详情链接；移除内推码和个人申请路径"),
    OfficialChinaSource("Shopee", "https://app.mokahr.com/campus_apply/shopee/2962", "active_public_api", "authoritative", "已接入校招、AI Star 人才计划和研发中心实习生招聘的完整公开分页列表"),
    OfficialChinaSource("JoinQuant", "https://app.mokahr.com/campus_apply/joinquant/92347", "active_public_api", "authoritative", "已接入职能、投研和技术类的完整公开分页岗位列表"),
    OfficialChinaSource("NVIDIA", "https://app.mokahr.com/campus-recruitment/nvidia/47111", "active_public_api", "authoritative", "已接入 2027 校招与实习的完整公开分页岗位列表"),
    OfficialChinaSource("腾讯音乐娱乐集团", "https://join.tencentmusic.com/", "official_public_board_review_pending", "disabled", "确认公开岗位列表、稳定职位 ID 和校招状态字段"),
    OfficialChinaSource("字节跳动", "https://jobs.bytedance.com/", "review_required", "disabled", "确认公开列表接口及分页/关闭语义"),
    OfficialChinaSource("快手", "https://campus.kuaishou.cn/recruit/campus/e/h5/#/campus/jobs", "active_public_api", "authoritative", "已接入公开 2027 届校招职位 API；每天增量同步，接口异常不会触发归档"),
    OfficialChinaSource("京东", "https://zhaopin.jd.com/", "review_required", "disabled", "确认校招筛选页和岗位关闭状态"),
    OfficialChinaSource("美团", "https://campus.meituan.com/", "review_required", "disabled", "确认官网岗位列表与详情字段"),
    OfficialChinaSource("腾讯", "https://join.qq.com/", "review_required", "disabled", "确认公开岗位列表与届别标记"),
    OfficialChinaSource("阿里巴巴", "https://talent.alibaba.com/", "review_required", "disabled", "确认招聘官网的公开可读数据合同"),
    OfficialChinaSource("小米", "https://hr.xiaomi.com/", "review_required", "disabled", "确认社招/校招/实习分类及状态字段"),
    OfficialChinaSource("网易", "https://campus.163.com/", "review_required", "disabled", "确认校招列表和官方详情链接"),
    OfficialChinaSource("联想", "https://talent.lenovo.com.cn/position", "active_public_api", "authoritative", "已接入完整公开分页职位列表、稳定职位 ID、JD 与官网详情链接"),
)


def china_source_catalog() -> list[dict[str, str]]:
    return [entry.to_dict() for entry in OFFICIAL_CHINA_SOURCE_CATALOG]

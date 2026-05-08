import os
import json
from typing import Any, Set


def remove_privacy_keys(obj: Any, keys_to_remove: Set[str]) -> Any:
    if isinstance(obj, dict):
        return {k: remove_privacy_keys(v, keys_to_remove)
                for k, v in obj.items() if k not in keys_to_remove}
    elif isinstance(obj, list):
        return [remove_privacy_keys(item, keys_to_remove) for item in obj]
    else:
        return obj


def process_and_save_json(input_path: str, output_path: str, privacy_keys: Set[str]) -> None:
    try:
        with open(input_path, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)

        cleaned_data = remove_privacy_keys(data, privacy_keys)

        with open(output_path, 'w', encoding='utf-8-sig') as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 成功清洗并归档: {os.path.basename(output_path)}")
    except Exception as e:
        print(f"❌ 处理文件 {input_path} 时出错: {e}")


def main():
    PRIVACY_KEYS = {
        "nickname", "userName", "avatar", "avatarUrl", "ownerId",
        "userNo", "userId", "userAvatar", "followerCount", "followingCount",
        "authorName", "username", "squareAuthorId", "authorAvatar",
        "authorLink", "authorIsVerified", "authorVerificationType", "authorRole",
        "shareLink", "mentionUserVOs", "userTag", "userLabels",
        "userGuideRecommendReasonInfo", "isLiked", "isFollowed", "followsYou",
        "isAddedToBookmark", "isReaction", "iosLink", "androidLink",
        "webLink", "featuredLink", "commentLink", "reportLink", "jumpLink",
        "quotedContentWebLink", "quotedContentDeepLink"
    }

    data_dir = "data"
    collect_dir = "data_collect"

    os.makedirs(collect_dir, exist_ok=True)

    if not os.path.exists(data_dir):
        print(f"⚠️ 源数据目录不存在: {data_dir}")
        return

    # 按字母顺序排序，确保时间靠后的文件在列表末尾
    data_files = sorted([f for f in os.listdir(data_dir) if f.endswith('.json')])
    if not data_files:
        print("📭 源数据目录中没有找到任何 .json 文件。")
        return

    existing_collect_files = set(os.listdir(collect_dir))

    # 取出最近 3 天的文件（如果总文件不足 3 个则全取）
    recent_files_count = min(3, len(data_files))
    recent_files = set(data_files[-recent_files_count:])

    # 逻辑：只要是没处理过的新文件，或者是最近 3 天的文件，统统扔进去洗
    files_to_process = [f for f in data_files if f not in existing_collect_files or f in recent_files]

    if not files_to_process:
        print("✨ 所有历史文件均已清洗完毕，没有需要处理的新文件。")
        return

    print(f"🚀 共发现 {len(files_to_process)} 个需要清洗的文件（含增量及最新覆盖）...")

    for filename in files_to_process:
        input_path = os.path.join(data_dir, filename)
        output_path = os.path.join(collect_dir, filename)
        process_and_save_json(input_path, output_path, PRIVACY_KEYS)

    print("\n🎉 本次数据清洗任务完成。")


if __name__ == "__main__":
    main()
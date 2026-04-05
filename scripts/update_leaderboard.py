#!/usr/bin/env python3
"""
龙虾AI排行榜 — 数据自动更新脚本
每小时通过 GitHub Actions 运行，从 Hugging Face API 获取最新数据
"""

import json
import urllib.request
import urllib.error
import os
from datetime import datetime, timezone, timedelta

# ---- Configuration ----
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'data', 'leaderboard.json')

HF_API_MODELS = 'https://huggingface.co/api/models'
HF_API_TRENDING = 'https://huggingface.co/api/trending'

# ---- Helper Functions ----
def fetch_json(url, timeout=30):
    """Fetch JSON from URL with error handling"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'LobsterAI-Leaderboard/1.0',
            'Accept': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"⚠️ Failed to fetch {url}: {e}")
        return None

def format_hf_model(model):
    """Extract key fields from HF model data"""
    model_id = model.get('id', '')
    parts = model_id.split('/')
    org = parts[0] if len(parts) > 1 else ''
    name = parts[1] if len(parts) > 1 else model_id

    # Extract license
    tags = model.get('tags', [])
    license_tag = 'Unknown'
    for t in tags:
        if t.startswith('license:'):
            license_tag = t.replace('license:', '').replace('-', ' ').title()
            break

    # Filter display tags
    display_tags = [t for t in tags if not any(t.startswith(p) for p in
        ['license:', 'dataset:', 'arxiv:', 'doi:', 'base_model:', 'eval-'])
        and t not in ['transformers', 'pytorch', 'safetensors', 'onnx', 'rust',
                       'jax', 'coreml', 'openvino', 'tf']
        and 'compatible' not in t and 'deploy:' not in t and 'region:' not in t
    ][:5]

    return {
        'id': model_id,
        'name': name,
        'org': org,
        'likes': model.get('likes', 0),
        'downloads': model.get('downloads', 0),
        'license': license_tag,
        'pipeline_tag': model.get('pipeline_tag', ''),
        'tags': display_tags,
        'created_at': model.get('createdAt', '')
    }

def format_trending_item(item):
    """Extract key fields from trending item"""
    repo_data = item.get('repoData', {})
    if not repo_data:
        # Trending might have flat structure
        return {
            'id': item.get('id', item.get('modelId', 'unknown')),
            'likes': item.get('likes', 0),
            'downloads': item.get('downloads', 0),
        }
    return {
        'id': repo_data.get('id', 'unknown'),
        'likes': repo_data.get('likes', 0),
        'downloads': repo_data.get('downloads', 0),
        'pipeline_tag': repo_data.get('pipeline_tag', '')
    }

# ---- Main Update Logic ----
def update_leaderboard():
    print("🦞 龙虾AI排行榜 — 开始数据更新...")

    # Load existing data
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ 已加载现有数据 (last updated: {data.get('lastUpdated', 'N/A')})")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️ 无法加载现有数据: {e}, 将创建新文件")
        data = {}

    updated = False

    # 1. Fetch HF Popular Models (by likes)
    print("\n📥 获取 Hugging Face 热门模型 (按点赞)...")
    hf_likes = fetch_json(f'{HF_API_MODELS}?sort=likes&direction=-1&limit=30&pipeline_tag=text-generation')
    if hf_likes:
        data['huggingface_top_likes'] = [format_hf_model(m) for m in hf_likes]
        print(f"   ✅ 获取到 {len(hf_likes)} 个模型")
        updated = True
    else:
        print("   ❌ 获取失败，保留旧数据")

    # 2. Fetch HF Popular Models (by downloads)
    print("\n📥 获取 Hugging Face 热门模型 (按下载)...")
    hf_downloads = fetch_json(f'{HF_API_MODELS}?sort=downloads&direction=-1&limit=30&pipeline_tag=text-generation')
    if hf_downloads:
        data['huggingface_top_downloads'] = [format_hf_model(m) for m in hf_downloads]
        print(f"   ✅ 获取到 {len(hf_downloads)} 个模型")
        updated = True
    else:
        print("   ❌ 获取失败，保留旧数据")

    # 3. Fetch Trending Models
    print("\n📥 获取 Hugging Face 趋势模型...")
    trending = fetch_json(HF_API_TRENDING)
    if trending:
        items = trending.get('recentlyTrending', trending if isinstance(trending, list) else [])
        if isinstance(items, list):
            data['trending'] = [format_trending_item(item) for item in items[:30]]
            print(f"   ✅ 获取到 {len(data['trending'])} 个趋势模型")
            updated = True
        else:
            print("   ❌ 趋势数据格式异常")
    else:
        print("   ❌ 获取失败，保留旧数据")

    # 4. Update timestamp
    if updated:
        beijing_tz = timezone(timedelta(hours=8))
        now = datetime.now(beijing_tz)
        data['lastUpdated'] = now.strftime('%Y-%m-%d %H:%M')
        data['lastUpdatedISO'] = now.isoformat()

        # Save
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 数据已更新! 时间: {data['lastUpdated']}")
        print(f"   文件: {DATA_FILE}")
    else:
        print("\n⚠️ 没有新数据更新")

    return updated

if __name__ == '__main__':
    update_leaderboard()

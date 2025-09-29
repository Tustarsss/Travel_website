import json
import codecs

# Read the regions.json file with proper encoding
with codecs.open('data/generated/regions.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

real_names = {
    '西湖景区', '清华大学', '北京大学', '中山大学', 
    '广州塔', '北京颐和园', '上海外滩', 
    '成都宽窄巷子', '西安大雁塔', '杭州灵隐寺'
}

real_count = sum(1 for r in data if r['name'] in real_names)
total_count = len(data)
synthetic_count = total_count - real_count

print(f'Real locations: {real_count}, Total: {total_count}, Synthetic: {synthetic_count}')

# Show first 10 entries to see how the data looks
print("\nFirst 10 entries:")
for i in range(min(10, len(data))):
    region = data[i]
    is_real = "REAL" if region['name'] in real_names else "SYNTHETIC"
    print(f"{i+1}. {region['name']} ({is_real}) - Type: {region['type']}, Coordinates: ({region['latitude']:.3f}, {region['longitude']:.3f})")
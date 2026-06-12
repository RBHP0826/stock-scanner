import json, time, random
d = json.load(open('shadowing_dictionary.json', encoding='utf-8'))
new_records = []
for r in d.get('records', []):
    new_details = [s for s in r.get('details', []) if s['rate'] >= 15.0 and s['amount'] >= 500]
    if new_details:
        r['details'] = new_details
        r['stocks'] = ', '.join([s['name'] for s in new_details])
        r['reason'] = ' | '.join([f"{s['name']}: {s['reason']}" for s in new_details])
        r['average_rate'] = round(sum(s['rate'] for s in new_details) / len(new_details), 2)
        r['cumulative_amount'] = int(sum(s['amount'] for s in new_details))
        new_records.append(r)
d['records'] = new_records

d['dictionary'] = []
for r in new_records:
    today_str = r['date']
    industry_groups = {}
    for s in r['details']:
        ind = s['industry']
        if ind not in industry_groups: industry_groups[ind] = []
        industry_groups[ind].append(s)
        
    for ind_name, stocks_in_ind in industry_groups.items():
        stock_count = len(stocks_in_ind)
        theme_tag = '[주도테마]' if stock_count >= 3 else '[개별이슈]'
        display_theme_name = f'{theme_tag} {ind_name}'
        
        ind_stocks_str = ', '.join([s['name'] for s in stocks_in_ind])
        ind_reasons_str = ' | '.join([f"{s['name']}: {s['reason']}" for s in stocks_in_ind])
        ind_avg_rate = round(sum(s['rate'] for s in stocks_in_ind) / stock_count, 2)
        ind_total_amount = int(sum(s['amount'] for s in stocks_in_ind))
        
        dict_idx = -1
        for idx, entry in enumerate(d['dictionary']):
            if ind_name in entry.get('theme', ''):
                dict_idx = idx
                break
        if dict_idx != -1:
            existing_stocks = [s.strip() for s in d['dictionary'][dict_idx]['stocks'].split(',') if s.strip()]
            for s in stocks_in_ind:
                if s['name'] not in existing_stocks:
                    existing_stocks.append(s['name'])
            d['dictionary'][dict_idx]['theme'] = display_theme_name
            d['dictionary'][dict_idx]['stocks'] = ', '.join(existing_stocks)
            d['dictionary'][dict_idx]['reason'] = f'({today_str} 업데이트) ' + ind_reasons_str
            d['dictionary'][dict_idx]['last_updated'] = today_str
            d['dictionary'][dict_idx]['average_rate'] = ind_avg_rate
            d['dictionary'][dict_idx]['cumulative_amount'] = ind_total_amount
        else:
            d['dictionary'].append({
                'id': f'theme_{random.randint(10000, 99999)}',
                'theme': display_theme_name,
                'keyword': ind_name,
                'stocks': ind_stocks_str,
                'reason': f'({today_str} 추가) ' + ind_reasons_str,
                'last_updated': today_str,
                'average_rate': ind_avg_rate,
                'cumulative_amount': ind_total_amount
            })
json.dump(d, open('shadowing_dictionary.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
print(f'Cleaned. Kept {len(new_records)} records.')

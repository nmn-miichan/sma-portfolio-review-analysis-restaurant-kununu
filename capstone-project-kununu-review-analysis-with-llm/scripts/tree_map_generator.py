import json
import plotly.graph_objects as go

def wrap_text_for_plotly(text, max_chars_per_line=20):
    if len(text) <= max_chars_per_line:
        return text
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    for word in words:
        if current_length + len(word) + 1 > max_chars_per_line and current_line:
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += len(word) + (1 if current_line else 0)
    if current_line:
        lines.append(' '.join(current_line))
    return '<br>'.join(lines)

def calculate_optimal_size(num_points, total_count):
    base_width = 1000
    base_height = 700
    width_factor = min(1.5, 1 + (num_points - 5) * 0.1) if num_points > 5 else 1
    height_factor = min(1.4, 1 + (num_points - 5) * 0.08) if num_points > 5 else 1
    count_factor = min(1.3, 1 + (total_count - 20) * 0.01) if total_count > 20 else 1
    width = int(base_width * width_factor * count_factor)
    height = int(base_height * height_factor * count_factor)
    width = max(800, min(1600, width))
    height = max(600, min(1200, height))
    return width, height

def get_treemap_figure(json_file_path, category, subcategory, width=None, height=None):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except Exception:
        return None

    categories = data.get('categories', [])
    category_data = None
    for cat in categories:
        if category in cat:
            category_data = cat[category]
            break
    if not category_data or subcategory not in category_data:
        return None

    points_data = category_data[subcategory]
    if not points_data:
        return None

    num_points = len(points_data)
    total_count = sum(point['count'] for point in points_data)
    if width is None or height is None:
        width, height = calculate_optimal_size(num_points, total_count)

    if subcategory == 'critical_points':
        root_color = '#E57373' 
        child_color = '#FFCDD2'
        title_color = '#d32f2f'
        line_color = '#d32f2f'
    else:
        root_color = '#81C784'
        child_color = '#C8E6C9'
        title_color = '#388e3c'
        line_color = '#388e3c'

    ids = []
    labels = []
    parents = []
    values = []
    colors = []
    hover_texts = []

    root_id = f"{category}_{subcategory}"
    root_label = f"{category.replace('_', ' ').title()}<br>{subcategory.replace('_', ' ').title()}"
    ids.append(root_id)
    labels.append(root_label)
    parents.append("")
    values.append(total_count)
    colors.append(root_color)
    hover_texts.append(f"<b>{category.replace('_', ' ').title()} - {subcategory.replace('_', ' ').title()}</b><br>Total Points: {num_points}<br>Total Mentions: {total_count}")

    sorted_points = sorted(points_data, key=lambda x: x['count'], reverse=True)
    for i, point in enumerate(sorted_points):
        point_text = point['point']
        references = point.get('references', [])
        hover_text = f"<b>{point_text}</b>"
        if references and isinstance(references, list):
            review_ids = [ref.get('review_id') for ref in references if ref.get('review_id')]
            if review_ids:
                hover_text += "<br><br><b>Review IDs:</b><br>" + "<br>".join(review_ids)

        point_id = f"{root_id}_point_{i}"

        ids.append(point_id)
        labels.append(wrap_text_for_plotly(point_text, 20))
        parents.append(root_id)
        values.append(point['count'])
        colors.append(child_color)
        hover_texts.append(hover_text)

    colors = [root_color] + [child_color] * (len(ids) - 1)

    fig = go.Figure(go.Treemap(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        marker=dict(
            colors=colors,
            line=dict(width=2, color=line_color)
        ),

        textinfo="label+value",
        textposition="middle center",
        textfont=dict(
            size=12,
            family="Arial, sans-serif",
            color="black"
        ),
        hovertemplate='%{customdata}<extra></extra>',
        customdata=hover_texts,
        maxdepth=2,
        pathbar=dict(visible=False)
    ))

    fig.update_layout(
        title={
            'text': f"<span style='font-size:14px; color:#666;'>{num_points} points • {total_count} total mentions</span>",
            'x': 0,
            'xanchor': 'left',
            'font': {'size': 20, 'color': title_color, 'family': 'Arial, sans-serif'}
        },
        font=dict(size=12, family='Arial, sans-serif'),
        width=width,
        height=height,
        margin=dict(t=50, l=10, r=40, b=50),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )

    return fig

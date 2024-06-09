import json
import os
from flask import Flask, render_template, request, send_from_directory
import pandas as pd
import psycopg2
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
import matplotlib.pyplot as plt


app = Flask(__name__)

# Database connection parameters
db_params = {
    "host": os.getenv("PG_HOST"),
    "port": os.getenv("PG_PORT"),
    "dbname": os.getenv("PG_DBNAME"),
    "user": os.getenv("PG_USER"),
    "password": os.getenv("PG_PASSWORD"),
}


def query_to_df(query):
    conn = psycopg2.connect(**db_params)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def df_to_json_tree(records):
    # Function to check if the value is JSON-serializable
    def is_json_serializable(value):
        try:
            json.dumps(value)
            return True
        except (TypeError, OverflowError):
            return False

    # Helper function to find or create the path in the tree
    def insert_node(path, node, tree):
        parts = path.split("/")
        current_level = tree
        for i, part in enumerate(parts[:-1]):
            current_path = "/".join(parts[: i + 1])
            for child in current_level:
                if child["absolute_path"] == current_path:
                    current_level = child.setdefault("children", [])
                    break
        # Add the final node
        current_level.append(node)

    # Initialize the root list
    hierarchy = []

    # Sort records by the prefix to ensure parent directories are handled first
    sorted_records = sorted(records, key=lambda x: x["prefix"])

    # Build the tree
    for record in sorted_records:
        path = record["prefix"]
        # Filter satellite data to only include JSON-serializable items
        node_data = {
            k: v for k, v in record.items() if k != "prefix" and is_json_serializable(v)
        }
        node_data["prefix"] = path.split("/")[
            -1
        ]  # Include only the basename in the prefix
        node_data["absolute_path"] = path  # Include the full path under 'absolute_path'
        node_data["parent"] = "/".join(path.split("/")[:-1]) or ""
        node_data["is_leaf"] = False
        insert_node(path, node_data, hierarchy)

    return hierarchy


def save_json_to_file(data, filename):
    with open(filename, "w") as json_file:
        json.dump(data, json_file, indent=4)


def json_tree_to_flat_list(json_tree, size_dimension):
    flat_list = []
    for item in json_tree:
        item["is_leaf"] = True
        if "children" in item:
            item["is_leaf"] = False
            item[f"{size_dimension}_for_ui"] = 0
            flat_list.extend(json_tree_to_flat_list(item["children"], size_dimension))
        else:
            item[f"{size_dimension}_for_ui"] = item[size_dimension]
        flat_list.append(item)
    return flat_list


def get_numeric_column_names_from_view(view_name):
    query = f"""
        SELECT attname AS column_name
        FROM pg_attribute
        WHERE attrelid = 's3dmap.{view_name}'::regclass
            AND NOT attisdropped
            AND attnum > 0
            AND format_type(atttypid, atttypmod) in (
                'int',
                'integer',
                'bigint',
                'smallint',
                'numeric',
                'decimal',
                'double',
                'double precision',
                'float',
                'real'
            )
        ORDER BY attnum;
    """
    df = query_to_df(query)
    return df.column_name.tolist()


def get_color_values_str(items, color_dimension):
    gradual_color_dimensions = get_numeric_column_names_from_view(os.getenv('PREFIXES_MATERIALIZED_VIEW'))
    if color_dimension not in gradual_color_dimensions:
        # Assign colors based on color_dimensions
        color_dimensions = list(
            set(str(item[color_dimension]) for item in items if color_dimension in item)
        )
        colors = plt.cm.tab20c.colors[: len(color_dimensions)]
        color_map = dict(zip(color_dimensions, colors))
        color_values = [
            color_map.get(str(item.get(color_dimension, None)), (1, 1, 1))
            for item in items
        ]
        color_values_str = [
            "rgba({}, {}, {}, 1)".format(int(255 * r), int(255 * g), int(255 * b))
            for r, g, b in color_values
        ]
    else:
        # Assign colors based on color_dimensions
        color_values = [item.get(color_dimension, 0) for item in items]
        # print min and max values
        print(f"min: {min(color_values)}, max: {max(color_values)}")
        colorscale = px.colors.sample_colorscale("plasma_r", 100000)
        color_values_str = []
        for value in [v - min(color_values) for v in color_values]:
            if value < 0:
                color_values_str.append(colorscale[0])
            elif max(color_values) == 0:
                color_values_str.append(colorscale[0])
            else:
                color_values_str.append(
                    colorscale[int((len(colorscale) - 1) * (value / max(color_values)))]
                )
    return color_values_str


def json_tree_to_figure(json_tree, size_dimension, color_dimension):
    items = json_tree_to_flat_list(json_tree, size_dimension)
    # save items json to file
    save_json_to_file(items, "items.json")

    # Extract attributes for the treemap
    ids = [item["absolute_path"] for item in items]
    parents = [item["parent"] for item in items]
    values = [item[f"{size_dimension}_for_ui"] for item in items]

    color_values_str = get_color_values_str(items, color_dimension)

    # Determine line widths (non-leaf nodes will have a border, leaf nodes won't)
    line_widths = [2 if not item["is_leaf"] else 0.5 for item in items]

    # Text information using the "value" key
    text_info = []
    for item in items:
        if item["is_leaf"]:
            text_info.append(
                f"<b>{item['prefix']}</b><br>{size_dimension}:{item[size_dimension]}<br>{color_dimension}:{item[color_dimension]}"
            )
        else:
            text_info.append(
                f"<b>{item['prefix']}</b> ({size_dimension}:{item[size_dimension]}, {color_dimension}:{item[color_dimension]})"
            )

    # Create treemap using the extracted attributes
    fig = go.Figure(
        go.Treemap(
            ids=ids,
            labels=text_info,
            parents=parents,
            values=values,
            marker_colors=color_values_str,
            marker_line_width=line_widths,
            marker_line_color="black",
            textinfo="label+percent root",  # Any combination of ['label', 'text', 'value', 'current path', 'percent root', 'percent entry', 'percent parent'] joined with '+' characters
            pathbar_visible=True,
            pathbar_textfont_size=15,
        )
    )

    fig.update_layout(
        margin=dict(t=0, l=0, r=0, b=0),
        height=1000,
    )
    return fig


@app.route("/generate_treemap", methods=["GET"])
def render_treemap():
    bucket = request.args.get("bucket", default="sample-bucket")
    filter_max_depth = int(request.args.get("filter_max_depth", default=100))
    size_dimension = request.args.get("size_dimension", default="sum_size")
    color_dimension = request.args.get(
        "color_dimension", default="count_distinct_suffix"
    )

    query = f"""
    SELECT * FROM {os.getenv('PREFIXES_DEMO_TABLE') if bucket == 'sample-bucket' else os.getenv('PREFIXES_MATERIALIZED_VIEW')}
    WHERE 1=1
        AND bucket = '{bucket}'
        AND depth <= {filter_max_depth if filter_max_depth > 0 else 1}
    ;"""
    df = query_to_df(query)

    json_tree = df_to_json_tree(df.to_dict(orient="records"))
    if not json_tree:
        return "<h3>No data found for the given bucket.</h3>"

    save_json_to_file(json_tree, "out.json")

    fig = json_tree_to_figure(json_tree, size_dimension, color_dimension)
    graph_html = pio.to_html(fig, full_html=False)

    return graph_html


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


if __name__ == "__main__":
    # Specify SSL context
    app.run(
        host="0.0.0.0",
        port=2323,
        ssl_context=("certs/cert.pem", "certs/key.pem"),
        debug=True,
    )

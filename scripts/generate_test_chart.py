import os
import matplotlib

matplotlib.use('Agg')  # 非交互式模式
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties


def generate_test_chart():
    font_path = 'C:/Windows/Fonts/msyh.ttc'  # Windows
    font = FontProperties(fname=font_path, size=12)


    # 创建目录
    os.makedirs("policy_images", exist_ok=True)

    # 生成示例数据
    labels = ['研发费用', '人才补贴', '基建投资']
    values = [45, 30, 25]

    # 绘制饼图
    plt.figure(figsize=(8, 6))
    plt.pie(values, labels=labels, autopct='%1.1f%%', textprops={'fontproperties': font})
    plt.title("政策资金分配比例", fontproperties=font)

    # 保存文件
    save_path = os.path.join("policy_images", "chart.png")
    plt.savefig(save_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"测试图表已生成至：{save_path}")


if __name__ == "__main__":
    generate_test_chart()
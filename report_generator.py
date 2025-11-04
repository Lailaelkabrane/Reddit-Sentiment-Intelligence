# report_generator.py (improved)

from datetime import datetime
from fpdf import FPDF
from io import BytesIO
import matplotlib.pyplot as plt
import pandas as pd
import tempfile
import os

class EnhancedPDFGenerator(FPDF):
    def __init__(self, df, search_term, analysis_date=None):
        super().__init__()
        self.df = df
        self.search_term = search_term
        self.analysis_date = analysis_date or datetime.now().strftime("%Y-%m-%d %H:%M")
        self.set_auto_page_break(auto=True, margin=15)
        self.temp_dir = tempfile.mkdtemp()
        self.set_font('Helvetica', '', 12)

    def generate_pdf(self):
        pdf_bytes = BytesIO()
        self._build_pdf_content()
        self.output(pdf_bytes)
        pdf_bytes.seek(0)

        # cleanup
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)
        return pdf_bytes

    def _save_chart(self, fig, filename):
        path = os.path.join(self.temp_dir, filename)
        fig.savefig(path, bbox_inches="tight", dpi=150)
        plt.close(fig)
        return path

    def _build_pdf_content(self):
        self.add_page()
        self._add_header()
        self._add_metrics_section()
             # now earlier
        self._add_visuals_section()
        self._add_recommendations()
        self._add_footer()

    def _add_header(self):
        self.set_font('Helvetica', 'B', 22)
        self.set_text_color(31, 78, 121)
        self.cell(0, 15, "Reddit Analysis Report", 0, 1, "C")
        self.set_font('Helvetica', 'I', 12)
        self.set_text_color(128, 128, 128)
        self.cell(0, 8, f"Generated on {self.analysis_date}", 0, 1, "C")
        self.ln(10)

    def _add_metrics_section(self):
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(31, 78, 121)
        self.cell(0, 10, "Key Metrics", 0, 1)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

        positive = len(self.df[self.df["Sentiment"] == "Positive"])
        negative = len(self.df[self.df["Sentiment"] == "Negative"])
        neutral = len(self.df[self.df["Sentiment"] == "Neutral"])

        metrics = [
            ("Search Term", self.search_term),
            ("Total Posts", str(len(self.df))),
            ("Avg Sentiment", f"{self.df['sentiment_compound'].mean():.2f}"),
            ("Positive Posts", f"{positive} ({positive/len(self.df)*100:.1f}%)"),
            ("Negative Posts", f"{negative} ({negative/len(self.df)*100:.1f}%)"),
            ("Neutral Posts", f"{neutral} ({neutral/len(self.df)*100:.1f}%)"),
        ]

        self.set_font("Helvetica", "", 12)
        for k, v in metrics:
            self.cell(60, 8, k, 0, 0, "L")
            self.cell(60, 8, v, 0, 1, "L")
        self.ln(5)

    

    def _add_visuals_section(self):
        # Sentiment Distribution
        if "Sentiment" in self.df.columns:
            counts = self.df["Sentiment"].value_counts()
            fig, ax = plt.subplots()
            counts.plot(kind="bar", color=["#4CAF50", "#FFC107", "#F44336"], ax=ax)
            ax.set_title("Sentiment Distribution")
            chart_path = self._save_chart(fig, "sentiment.png")
            self.image(chart_path, x=25, w=160)
            self.ln(60)

        # Trend chart
        if "date" in self.df.columns:
            trend = self.df.groupby("date")["sentiment_compound"].mean()
            fig, ax = plt.subplots()
            trend.plot(ax=ax, marker="o", color="#2196F3")
            ax.set_title("Daily Average Sentiment")
            ax.set_ylabel("Sentiment Score")
            chart_path = self._save_chart(fig, "trend.png")
            self.image(chart_path, x=25, w=160)
            self.ln(60)

        # Industry chart
        if "industry" in self.df.columns:
            grouped = self.df.groupby("industry")["sentiment_compound"].agg(["mean", "count"]).head(5)
            fig, ax1 = plt.subplots()
            grouped["count"].plot(kind="bar", ax=ax1, alpha=0.6, color="#9E9E9E")
            ax2 = ax1.twinx()
            ax2.plot(grouped.index, grouped["mean"], color="#FF5722", marker="o")
            ax1.set_title("Industry Analysis (Top 5)")
            chart_path = self._save_chart(fig, "industry.png")
            self.image(chart_path, x=25, w=160)
            self.ln(70)

    def _add_recommendations(self):
     self.set_font('Helvetica', 'B', 16)
     self.set_text_color(31, 78, 121)
     self.cell(0, 10, "Insights & Recommendations", 0, 1)
     self.line(10, self.get_y(), 200, self.get_y())
     self.ln(5)

     recommendations = [
        "Monitor spikes in negative sentiment to identify potential PR crises early.",
        "Leverage positive discussions by engaging with supportive communities.",
        "Consider deeper analysis by industry or region for targeted strategies.",
        "Export the dataset regularly for offline review and archiving.",
     ]

     self.set_font("Helvetica", "", 11)
     page_width = self.w - 2 * self.l_margin  # safe width

     for line in recommendations:
        self.multi_cell(page_width, 6, f"- {line}", 0, "L")
        self.ln(2)

     self.ln(5)

    def _add_footer(self):
        self.ln(5)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 5, "Generated by Reddit Sentiment Dashboard", 0, 0, "C")

    def generate_json(self):
        pos = len(self.df[self.df["Sentiment"] == "Positive"])
        neg = len(self.df[self.df["Sentiment"] == "Negative"])
        neu = len(self.df[self.df["Sentiment"] == "Neutral"])
        return {
            "metadata": {"search_term": self.search_term, "analysis_date": self.analysis_date, "total_posts": len(self.df)},
            "metrics": {
                "average_sentiment": float(self.df["sentiment_compound"].mean()),
                "distribution": {"positive": pos, "negative": neg, "neutral": neu},
            },
            "top_posts": self.df.nlargest(5, "score")[["title", "Sentiment", "score", "num_comments"]].to_dict(orient="records"),
        }

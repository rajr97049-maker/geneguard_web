from flask import Flask, render_template, request, redirect, send_file, send_from_directory
import json, os
from werkzeug.utils import secure_filename

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# AI + OCR
import fitz
import pytesseract
from PIL import Image

app = Flask(__name__)

FILE = "data.json"
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ✅ CREATE UPLOAD FOLDER (IMPORTANT FOR RENDER)
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ⚠️ OPTIONAL (only needed locally for image OCR)
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ---------- DATA ----------
def load_data():
    if os.path.exists(FILE):
        with open(FILE, "r") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(FILE, "w") as f:
        json.dump(data, f)

# ---------- TEXT EXTRACTION ----------
def extract_text(filepath):
    text = ""
    try:
        if filepath.endswith(".pdf"):
            doc = fitz.open(filepath)
            for page in doc:
                text += page.get_text()

        elif filepath.endswith((".png", ".jpg", ".jpeg")):
            img = Image.open(filepath)
            text = pytesseract.image_to_string(img)

        elif filepath.endswith(".txt"):
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
    except:
        pass
    return text.lower()

# ---------- AI ----------
def analyze_ai(text, symptoms, relation):
    text = text.lower()
    symptoms = symptoms.lower()

    disease_rules = {
        "Dengue": {"keywords": ["platelet","ns1","fever","rash"], "genetic": False},
        "Heart Disease": {"keywords": ["cholesterol","bp","heart","chest pain"], "genetic": True},
        "Diabetes": {"keywords": ["glucose","sugar","diabetes"], "genetic": True},
        "Cancer": {"keywords": ["tumor","cancer"], "genetic": True},
        "Infection": {"keywords": ["infection","virus","bacteria"], "genetic": False}
    }

    score = {}
    genetic_flag = False

    for disease, info in disease_rules.items():
        score[disease] = 0

        for word in info["keywords"]:
            if word in text:
                score[disease] += 30
            if word in symptoms:
                score[disease] += 20

        if relation.lower() in ["father","mother","grandfather","grandmother"]:
            if info["genetic"] and score[disease] > 0:
                genetic_flag = True

    best = max(score, key=score.get)
    percent = score[best]

    if percent == 0:
        return "Low Risk", "No genetic link"

    genetic_text = "Genetic Risk Possible" if genetic_flag else "Not Genetic"

    return f"{best} ({percent}%)", genetic_text

# ---------- HOME ----------
@app.route("/", methods=["GET", "POST"])
def index():
    data = load_data()

    if request.method == "POST":
        file = request.files.get("file")
        filename = ""
        path = ""

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(path)

        symptoms = request.form.get("symptoms", "")
        text = extract_text(path) if filename else ""

        ai_result, genetic = analyze_ai(text, symptoms, request.form["relation"])

        data.append({
            "name": request.form["name"],
            "relation": request.form["relation"],
            "age": request.form["age"],
            "symptoms": symptoms,
            "report": request.form.get("report", ""),
            "file": filename,
            "ai": ai_result,
            "genetic": genetic
        })

        save_data(data)
        return redirect("/")

    return render_template("index.html", data=data)

# ---------- DELETE ----------
@app.route("/delete/<int:id>")
def delete(id):
    data = load_data()
    if id < len(data):
        data.pop(id)
    save_data(data)
    return redirect("/")

# ---------- VIEW FILE ----------
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ---------- PDF ----------
@app.route("/report/<int:id>")
def report(id):
    data = load_data()

    if id >= len(data):
        return "No data"

    m = data[id]
    filename = f"{m['name']}_report.pdf"

    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("GeneGuard Medical Report", styles["Title"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Name: {m['name']}", styles["Normal"]))
    content.append(Paragraph(f"Relation: {m['relation']}", styles["Normal"]))
    content.append(Paragraph(f"Age: {m['age']}", styles["Normal"]))
    content.append(Paragraph(f"Symptoms: {m['symptoms']}", styles["Normal"]))
    content.append(Paragraph(f"AI Risk: {m['ai']}", styles["Normal"]))
    content.append(Paragraph(f"Genetic: {m['genetic']}", styles["Normal"]))

    content.append(Spacer(1, 10))
    content.append(Paragraph("Doctor Notes:", styles["Heading2"]))
    content.append(Paragraph(m.get("report", "No notes"), styles["Normal"]))

    doc.build(content)

    return send_file(filename, as_attachment=True)

# ---------- RUN ----------
if __name__ == "__main__":
    app.run()
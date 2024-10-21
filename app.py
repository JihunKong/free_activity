import streamlit as st
from openai import OpenAI
import pandas as pd
from fpdf import FPDF
import io
import datetime
from io import BytesIO

# 세션 상태 초기화
if 'students' not in st.session_state:
    st.session_state.students = {}

if 'reports' not in st.session_state:
    st.session_state.reports = {}

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=st.secrets["openai"]["api_key"])

def generate_report(student_info, activities, template):
    prompt = f"""
    학생 정보: {student_info}
    
    다음은 고등학교 1학년 학생의 자율활동 내용입니다:
    {activities}
    
    템플릿: {template}
    
    위 정보를 바탕으로 자율활동 세부능력 및 특기사항을 작성해주세요. 
    학생의 자기주도성, 리더십, 공동체 의식, 문제해결 능력 등이 잘 드러나도록 작성해주세요.
    구체적인 활동 내용과 그로 인한 성과, 학생의 성장을 포함해주세요.
    제공된 템플릿의 스타일을 따라주세요. 단, 한 문단으로 표현해야 합니다.
    모든 문장은 '-함.', '-음.', '-됨.' 등으로 끝나야 합니다.
    최대한 미사여구를 많이 포함하도록 하세요. 학생의 이름과 '학생은'이라는 주어는 생략하세요.
    """
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 대한민국 최고의 입시컨설턴트로서 학생들의 자율활동 세특을 작성하는 전문가입니다."},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"세특 생성 중 오류 발생: {str(e)}")
        return None

def create_pdf(student_name, report_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('NanumGothic', '', 'NanumGothic.ttf', uni=True)
    pdf.set_font("NanumGothic", size=12)
    pdf.cell(200, 10, txt=f"자율활동 세부능력 및 특기사항: {student_name}", ln=1, align='C')
    pdf.multi_cell(0, 10, txt=report_text)
    return pdf.output(dest='S').encode('utf-8')

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data

def save_report(student_id, report):
    if student_id not in st.session_state.reports:
        st.session_state.reports[student_id] = []
    st.session_state.reports[student_id].append(report)

st.title("자율활동 세부능력 및 특기사항 생성기")

# 사이드바 메뉴
menu = st.sidebar.selectbox("메뉴 선택", ["학생 정보 관리", "세특 생성", "세특 생성 히스토리"])

if menu == "학생 정보 관리":
    st.subheader("학생 정보 관리")
    student_name = st.text_input("학생 이름")
    student_id = st.text_input("학번")
    student_class = st.text_input("학급")
    
    if st.button("학생 정보 저장"):
        st.session_state.students[student_id] = {
            "name": student_name,
            "class": student_class
        }
        st.success("학생 정보가 저장되었습니다.")
    
    st.subheader("등록된 학생 목록")
    st.table(pd.DataFrame(st.session_state.students).T)

elif menu == "세특 생성":
    st.subheader("세특 생성")
    
    student_id = st.selectbox("학생 선택", list(st.session_state.students.keys()))
    student_info = st.session_state.students.get(student_id, {})
    
    activity_categories = ["학급 및 학교 활동", "자기주도적 활동", "공동체 활동", "창의적 문제해결 활동", "진로탐색 활동", "기타 활동"]
    activities = {}
    for category in activity_categories:
        activities[category] = st.text_area(f"{category} 내용:")
    
    templates = ["상세형", "요약형", "성과중심형"]
    selected_template = st.selectbox("세특 템플릿 선택", templates)
    
    if st.button("세특 생성"):
        if student_info and any(activities.values()):
            formatted_activities = "\n".join([f"{cat}: {act}" for cat, act in activities.items() if act])
            report = generate_report(student_info, formatted_activities, selected_template)
            if report:
                st.subheader("생성된 세특:")
                st.write(report)
                
                edited_report = st.text_area("생성된 세특을 수정하세요:", value=report, height=300)
                if st.button("수정된 세특 저장"):
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    new_report = {"timestamp": timestamp, "report": edited_report}
                    save_report(student_id, new_report)
                    st.success("세특이 성공적으로 저장되었습니다!")
                    
                    # PDF 생성 및 다운로드 버튼
                    pdf = create_pdf(student_info['name'], edited_report)
                    st.download_button(
                        label="PDF 다운로드",
                        data=pdf,
                        file_name=f"{student_info['name']}_자율활동세특_{timestamp}.pdf",
                        mime="application/pdf"
                    )
        else:
            st.warning("학생 정보와 최소 하나의 활동 내용을 입력해주세요.")

elif menu == "세특 생성 히스토리":
    st.subheader("세특 생성 히스토리")
    student_id = st.selectbox("학생 선택", list(st.session_state.students.keys()))
    if student_id in st.session_state.reports:
        reports_data = []
        for i, report in enumerate(st.session_state.reports[student_id]):
            st.write(f"세특 {i+1} - {report['timestamp']}")
            st.text_area(f"세특 내용 {i+1}", report['report'], height=150)
            st.download_button(
                label=f"PDF 다운로드 {i+1}",
                data=create_pdf(st.session_state.students[student_id]['name'], report['report']),
                file_name=f"{st.session_state.students[student_id]['name']}_활동보고서_{report['timestamp']}.pdf",
                mime="application/pdf"
            )
            reports_data.append({"timestamp": report['timestamp'], "report": report['report']})
        
        # 엑셀 다운로드 버튼 추가
        df = pd.DataFrame(reports_data)
        excel_data = to_excel(df)
        st.download_button(
            label="엑셀로 모든 세특 다운로드",
            data=excel_data,
            file_name=f"{st.session_state.students[student_id]['name']}_모든_세특.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("저장된 세특이 없습니다.")

st.sidebar.header("사용 안내")
st.sidebar.write("""
1. '학생 정보 관리' 메뉴에서 학생 정보를 입력하고 저장합니다.
2. '세특 생성' 메뉴에서 학생을 선택하고 활동 내용을 입력합니다.
3. 원하는 세특 템플릿을 선택하고 '세특 생성' 버튼을 클릭합니다.
4. 생성된 세특을 확인하고 필요한 경우 수정합니다.
5. '수정된 세특 저장' 버튼을 클릭하여 세특을 저장하고 PDF로 다운로드할 수 있습니다.
6. '세특 생성 히스토리' 메뉴에서 이전에 생성한 세특들을 확인하고 PDF 또는 엑셀 형식으로 다운로드할 수 있습니다.
""")

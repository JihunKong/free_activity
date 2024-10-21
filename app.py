import streamlit as st
import openai as OpenAI
import pandas as pd
import fpdf as FPDF
import io
import datetime

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=st.secrets["openai"]["api_key"])

# 데이터베이스 대신 세션 상태를 사용
if 'students' not in st.session_state:
    st.session_state.students = {}

if 'reports' not in st.session_state:
    st.session_state.reports = {}

def generate_report(student_info, activities, template):
    prompt = f"""
    학생 정보: {student_info}
    
    다음은 고등학교 1학년 학생의 자율활동 내용입니다:
    {activities}
    
    템플릿: {template}
    
    위 정보를 바탕으로 자율활동 세부능력 및 특기사항을 작성해주세요. 
    학생의 자기주도성, 리더십, 공동체 의식, 문제해결 능력 등이 잘 드러나도록 작성해주세요.
    구체적인 활동 내용과 그로 인한 성과, 학생의 성장을 포함해주세요.
    제공된 템플릿의 스타일을 따라주세요.
    """
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 학생들의 자율활동 보고서를 작성하는 전문가입니다."},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"보고서 생성 중 오류 발생: {str(e)}")
        return None

def create_pdf(student_name, report_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"자율활동 세부능력 및 특기사항: {student_name}", ln=1, align='C')
    pdf.multi_cell(0, 10, txt=report_text)
    return pdf.output(dest='S').encode('latin-1')

st.title("자율활동 세부능력 및 특기사항 생성기")

# 사이드바 메뉴
menu = st.sidebar.selectbox("메뉴 선택", ["학생 정보 관리", "보고서 생성", "보고서 히스토리"])

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

elif menu == "보고서 생성":
    st.subheader("보고서 생성")
    
    student_id = st.selectbox("학생 선택", list(st.session_state.students.keys()))
    student_info = st.session_state.students.get(student_id, {})
    
    activity_categories = ["학급 및 학교 활동", "자기주도적 활동", "공동체 활동", "창의적 문제해결 활동", "진로탐색 활동", "기타 활동"]
    activities = {}
    for category in activity_categories:
        activities[category] = st.text_area(f"{category} 내용:")
    
    templates = ["상세형", "요약형", "성과중심형"]
    selected_template = st.selectbox("보고서 템플릿 선택", templates)
    
    if st.button("보고서 생성"):
        if student_info and any(activities.values()):
            formatted_activities = "\n".join([f"{cat}: {act}" for cat, act in activities.items() if act])
            report = generate_report(student_info, formatted_activities, selected_template)
            if report:
                st.subheader("생성된 보고서:")
                st.write(report)
                
                edited_report = st.text_area("생성된 보고서를 수정하세요:", value=report, height=300)
                if st.button("수정된 보고서 저장"):
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if student_id not in st.session_state.reports:
                        st.session_state.reports[student_id] = []
                    st.session_state.reports[student_id].append({"timestamp": timestamp, "report": edited_report})
                    st.success("보고서가 성공적으로 저장되었습니다!")
                    
                    # PDF 생성 및 다운로드 버튼
                    pdf = create_pdf(student_info['name'], edited_report)
                    st.download_button(
                        label="PDF 다운로드",
                        data=pdf,
                        file_name=f"{student_info['name']}_활동보고서_{timestamp}.pdf",
                        mime="application/pdf"
                    )
        else:
            st.warning("학생 정보와 최소 하나의 활동 내용을 입력해주세요.")

elif menu == "보고서 히스토리":
    st.subheader("보고서 히스토리")
    student_id = st.selectbox("학생 선택", list(st.session_state.students.keys()))
    if student_id in st.session_state.reports:
        for i, report in enumerate(st.session_state.reports[student_id]):
            st.write(f"보고서 {i+1} - {report['timestamp']}")
            st.text_area(f"보고서 내용 {i+1}", report['report'], height=150)
            st.download_button(
                label=f"PDF 다운로드 {i+1}",
                data=create_pdf(st.session_state.students[student_id]['name'], report['report']),
                file_name=f"{st.session_state.students[student_id]['name']}_활동보고서_{report['timestamp']}.pdf",
                mime="application/pdf"
            )
    else:
        st.info("저장된 보고서가 없습니다.")

st.sidebar.header("사용 안내")
st.sidebar.write("""
1. '학생 정보 관리' 메뉴에서 학생 정보를 입력하고 저장합니다.
2. '보고서 생성' 메뉴에서 학생을 선택하고 활동 내용을 입력합니다.
3. 원하는 보고서 템플릿을 선택하고 '보고서 생성' 버튼을 클릭합니다.
4. 생성된 보고서를 확인하고 필요한 경우 수정합니다.
5. '수정된 보고서 저장' 버튼을 클릭하여 보고서를 저장하고 PDF로 다운로드할 수 있습니다.
6. '보고서 히스토리' 메뉴에서 이전에 생성한 보고서들을 확인하고 다운로드할 수 있습니다.
""")

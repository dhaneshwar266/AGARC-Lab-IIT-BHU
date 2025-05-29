import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv
load_dotenv()
import requests

# couter for visits
def get_user_country():
    try:
        forwarded_for = request.headers.get('X-Forwarded-For', '')
        ip = forwarded_for.split(',')[0] if forwarded_for else request.remote_addr

        # Log to debug
        print(f"Client IP: {ip}")

        if ip.startswith('127.') or ip.startswith('10.') or ip.startswith('192.') or ip == '::1':
            return 'Unknown'

        res = requests.get(f'https://ipapi.co/{ip}/json/')
        if res.status_code == 200:
            country = res.json().get('country_name')
            return country if country else 'Unknown'
    except Exception as e:
        print("GeoIP error:", e)
    return 'Unknown'


app = Flask(__name__)

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME") ,  # Replace with your cloud name
    api_key=os.getenv("CLOUDINARY_API_KEY"),        # Replace with your API key
    api_secret=os.getenv("CLOUDINARY_API_SECRET")   # Replace with your API secret
)

# Firebase initialization
firebase_config = {
    "type": os.getenv("FIREBASE_TYPE"),
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL")
}


cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv("FIREBASE_DATABASE_URL")
})



# ---mail configuration---
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT"))
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS") == "True"
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER")

mail = Mail(app)

# --- Routes ---
app.secret_key = os.getenv("SECRET_KEY")  # Set a secret key for session management

@app.route('/')
def index():
    # Increment visit counter
    counter_ref = db.reference('visits')
    current_count = counter_ref.get() or 0
    counter_ref.set(current_count + 1)
    
    # Country-wise count
    country = get_user_country()
    country_ref = db.reference(f'country_visits/{country}')
    current_country_count = country_ref.get() or 0
    country_ref.set(current_country_count + 1)
    
    # Get active notices for the notice board
    notices_ref = db.reference('notices')
    notices = notices_ref.get()
    active_notices = []
    
    if notices:
        for key, notice in notices.items():
            if notice.get('active', True):  # Only show active notices
                notice['id'] = key
                active_notices.append(notice)
    
    # Sort notices by date in descending order and take only the first 3
    active_notices.sort(key=lambda x: x.get('date', ''), reverse=True)
    active_notices = active_notices[:3]
    
    # Get slides for the sliding images section
    slides_ref = db.reference('home/slides')
    slides = slides_ref.get()
    slides_list = []
    
    if slides:
        for key, slide in slides.items():
            slide['id'] = key
            slides_list.append(slide)
        # Sort slides by order
        slides_list.sort(key=lambda x: x.get('order', 0))
    
    # Get drones for the showcase section
    drones_ref = db.reference('home/drones')
    drones = drones_ref.get()
    drones_list = []
    
    if drones:
        for key, drone in drones.items():
            drone['id'] = key
            drones_list.append(drone)
    
    # Fetch country-wise view counts
    country_views_ref = db.reference('country_visits')
    country_views = country_views_ref.get() or {}
    # Remove 'Unknown' from top list unless needed
    sorted_country_views = sorted(country_views.items(), key=lambda x: x[1], reverse=True)

    # Always include India if it exists
    top_countries = [item for item in sorted_country_views if item[0] != 'Unknown']
    india_entry = next((item for item in sorted_country_views if item[0] == 'India'), None)

    # Add India manually if not already in top_countries
    if india_entry and india_entry not in top_countries:
        top_countries.insert(0, india_entry)

    # Limit to 5, include 'Unknown' if needed to fill
    if len(top_countries) < 5:
        unknown_entry = next((item for item in sorted_country_views if item[0] == 'Unknown'), None)
    if unknown_entry:
        top_countries.append(unknown_entry)

    top_countries = top_countries[:5]        
    
    return render_template('index.html', 
                         notices=active_notices,
                         slides=slides_list,
                         drones=drones_list,
                         visit_count=current_count + 1,
                         country_views=top_countries)

@app.route('/about')
def about():
    # Get about data from Firebase
    about_ref = db.reference('about')
    about_data = about_ref.get()
    
   # Initialize default values if about_data is None or missing required fields
    if about_data is None or 'welcome_text' not in about_data:
        default_data = {
            'team_members': 0,
            'active_projects': 0,
            'trained_interns': 0,
            'publications': 0,
            'welcome_text': {
                'title': 'Welcome to AGARC',
                'content': 'The Aero-Ground Autonomy Research Center at the Department of Electrical Engineering, IIT (BHU) Varanasi is a pioneering hub for advanced research in autonomous systems. Established through the prestigious I-DAPT HUB Foundation grant under the project entitled "Centre for Development of Drone Related Technologies",2023, and in strategic collaboration with Quanser, the centre operates under the leadership of Prof. Shyam Kamal, the Principal Investigator. This centre stands at the forefront of innovation in aerial and ground robotics, intelligent control systems, and AI-driven autonomy. With a vibrant team of PhD scholars, MTech researchers, and several BTech project groups, it fosters a dynamic environment for cutting-edge research and hands-on technological development. Utilizing state-of-the-art platforms such as Quanser QDrone2 and QBot Platform, the centre is advancing the frontiers of swarm robotics, machine learning, and real-time autonomous navigation'
            },
            'facilities': [
                {
                    'icon': 'fas fa-helicopter',
                    'title': 'UAV & UGV Platforms',
                    'description': 'Advanced Unmanned Arial Vehical & Unmanned Ground Vehicle research platforms equipped with multisensor fusion and precision control'
                },
                {
                    'icon': 'fas fa-users-cog',
                    'title': 'Colaborative Research & Testing Facilities',
                    'description': 'Industry-academia collaborative research hub advancing autonomous systems through shared innovation'
                },
                {
                    'icon': 'fas fa-crosshairs',
                    'title': 'High Precision Autonomous Systems',
                    'description': 'High-resolution cameras and sensors'
                },
                {
                    'icon': 'fas fa-laptop-code',
                    'title': 'Software Lab',
                    'description': 'Advanced programming and simulation tools'
                }
            ]
        }
        
        # If about_data exists but is missing fields, merge with default data
        if about_data is not None:
            default_data.update(about_data)
        
        # Update the database with the complete structure
        about_ref.set(default_data)
        about_data = default_data
    
    return render_template('about.html', about=about_data)

@app.route('/team')
def team():
    # Get team leads
    team_leads_ref = db.reference('team_leads')
    team_leads = team_leads_ref.get()
    if team_leads:
        team_leads = [{'id': k, **v} for k, v in team_leads.items()]
        team_leads.sort(key=lambda x: x.get('order', 0))
    else:
        team_leads = []
    
    # Get faculty members
    faculty_ref = db.reference('faculty')
    faculty_members = faculty_ref.get()
    if faculty_members:
        faculty_members = [{'id': k, **v} for k, v in faculty_members.items()]
        faculty_members.sort(key=lambda x: x.get('order', 0))
    else:
        faculty_members = []
    
    # Get team members
    team_ref = db.reference('team')
    team_members = team_ref.get()
    if team_members:
        team_members = [{'id': k, **v} for k, v in team_members.items()]
        team_members.sort(key=lambda x: x.get('order', 0))
    else:
        team_members = []
    
    # Get pass-out members
    passout_ref = db.reference('passout_members')
    passout_members = passout_ref.get()
    if passout_members:
        passout_members = [{'id': k, **v} for k, v in passout_members.items()]
        passout_members.sort(key=lambda x: x.get('passout_year', 0), reverse=True)
    else:
        passout_members = []
    
    return render_template('team.html', 
                         team_leads=team_leads,
                         faculty_members=faculty_members,
                         team_members=team_members,
                         passout_members=passout_members)

@app.route('/research')
def research():
    publications_ref = db.reference('research/publications')
    projects_ref = db.reference('research/projects')
    
    publications = publications_ref.get()
    projects = projects_ref.get()
    
    publications_list = []
    projects_list = []
    
    if publications:
        for key, publication in publications.items():
            publication['id'] = key
            publications_list.append(publication)
        # Sort publications by date in descending order
        publications_list.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    if projects:
        for key, project in projects.items():
            project['id'] = key
            projects_list.append(project)
        # Sort projects by date in descending order
        projects_list.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return render_template('research.html', 
                         publications=publications_list,
                         projects=projects_list)

@app.route('/gallery')
def gallery():
    gallery_ref = db.reference('gallery')
    items = gallery_ref.get()
    images_list = []
    videos_list = []
    
    if items:
        for key, item in items.items():
            item['id'] = key
            if item.get('type') == 'video':
                videos_list.append(item)
            else:
                images_list.append(item)
        
        # Sort both lists by date in descending order
        images_list.sort(key=lambda x: x.get('date', ''), reverse=True)
        videos_list.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return render_template('gallery.html', images=images_list, videos=videos_list)

@app.route('/notice')
def notice():
    notices_ref = db.reference('notices')
    notices = notices_ref.get()
    notices_list = []
    
    if notices:
        for key, notice in notices.items():
            if notice.get('active', True):  # Only show active notices
                notice['id'] = key
                notices_list.append(notice)
    
    # Sort notices by date in descending order
    notices_list.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return render_template('notice.html', notices=notices_list)

@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        data = request.form
        name = data.get('name')
        email = data.get('email')
        subject = data.get('subject')
        message = data.get('message')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Save to Firebase Realtime Database
        ref = db.reference('messages')
        ref.push({
            "name": name,
            "email": email,
            "subject": subject,
            "message": message,
            "timestamp": timestamp
        })
        # Send email
        msg = Message(subject=f"New Contact Form Message: {subject}",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=['agarc.cdrt@gmail.com'])
        msg.body = f"""
        You received a new message from your website contact form.

        Name: {name}
        Email: {email}
        Subject: {subject}
        Message: {message}
        Sent at: {timestamp}
        """
        mail.send(msg)


        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Message sent successfully!'})

        return render_template('contact.html')
    return render_template('contact.html')



@app.route('/admin_messages')
def admin_messages():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    messages_ref = db.reference('messages')
    messages = messages_ref.get()
    messages_list = []
    
    if messages:
        for key, message in messages.items():
            message['id'] = key
            messages_list.append(message)
        # Sort messages by timestamp in descending order
        messages_list.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return render_template('admin_messages.html', messages=messages_list)


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        session.pop('user_id', None)  # Clear any existing session

        if (request.form.get('pass') == os.getenv("ADMIN_PASSWORD") and request.form.get('uname') == os.getenv("ADMIN_USERNAME")):
            session['user_id'] = request.form.get('uname')
            return redirect('/admin_dashboard')
        
    if 'user_id' in session:
        return redirect('/admin_dashboard')
    return render_template('admin_login.html')

@app.route('/admin_logout')
def admin_logout():
    session.pop('user_id', None)
    return redirect('/admin_login')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    # Get counts for dashboard
    messages_ref = db.reference('messages')
    messages = messages_ref.get()
    new_messages_count = len(messages) if messages else 0
    
    # Get recent messages (last 5)
    recent_messages = []
    if messages:
        for key, message in list(messages.items())[-5:]:
            message['id'] = key
            recent_messages.append(message)
    
    # Get notices count
    notices_ref = db.reference('notices')
    notices = notices_ref.get()
    notices_count = len(notices) if notices else 0
    
    # Get team count
    team_ref = db.reference('team')
    team = team_ref.get()
    team_count = len(team) if team else 0
    
    return render_template('admin_dashboard.html',
                         new_messages_count=new_messages_count,
                         notices_count=notices_count,
                         team_count=team_count,
                         recent_messages=recent_messages)

@app.route('/admin_notice')
def admin_notice():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    notices_ref = db.reference('notices')
    notices = notices_ref.get()
    notices_list = []
    
    if notices:
        for key, notice in notices.items():
            notice['id'] = key
            notices_list.append(notice)
    
    return render_template('admin_notice.html', notices=notices_list)

@app.route('/admin_notice/add', methods=['POST'])
def add_notice():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    title = request.form.get('title')
    content = request.form.get('content')
    active = request.form.get('active') == 'on'
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pdf = request.files.get('pdf')
    pdf_url = None
    if pdf and pdf.filename:
        result = cloudinary.uploader.upload(
            pdf,
            folder="notices/pdfs",
            resource_type="raw"
        )
        pdf_url = result['secure_url']
    notice_data = {
        'title': title,
        'content': content,
        'active': active,
        'date': date,
        'pdf_url': pdf_url
    }
    notices_ref = db.reference('notices')
    notices_ref.push(notice_data)
    return redirect('/admin_notice')

@app.route('/admin_notice/edit/<notice_id>', methods=['GET', 'POST'])
def edit_notice(notice_id):
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    notices_ref = db.reference(f'notices/{notice_id}')
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        active = request.form.get('active') == 'on'
        
        notice_data = {
            'title': title,
            'content': content,
            'active': active
        }
        
        notices_ref.update(notice_data)
        return redirect('/admin_notice')
    
    notice = notices_ref.get()
    if notice:
        notice['id'] = notice_id
        return render_template('admin_notice_edit.html', notice=notice)
    
    return redirect('/admin_notice')

@app.route('/admin_notice/delete/<notice_id>', methods=['DELETE'])
def delete_notice(notice_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    notices_ref = db.reference(f'notices/{notice_id}')
    notices_ref.delete()
    
    return jsonify({'success': True})

# Gallery Management
@app.route('/admin_gallery')
def admin_gallery():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    gallery_ref = db.reference('gallery')
    items = gallery_ref.get()
    items_list = []
    
    if items:
        for key, item in items.items():
            item['id'] = key
            items_list.append(item)
        
        # Sort items by date in descending order
        items_list.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return render_template('admin_gallery.html', items=items_list)

@app.route('/admin_gallery/add', methods=['POST'])
def add_gallery_image():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    title = request.form.get('title')
    image = request.files.get('image')
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if image:
        # Upload image to Cloudinary
        result = cloudinary.uploader.upload(image,
            folder="gallery",  # Images will be stored in a 'gallery' folder
            resource_type="image",
            transformation=[
                {'width': 1000, 'crop': "scale"},  # Resize image to max width of 1000px
                {'quality': "auto"}  # Automatic quality optimization
            ]
        )
        image_url = result['secure_url']  # Get the secure URL of the uploaded image
    else:
        image_url = None
    
    image_data = {
        'title': title,
        'url': image_url,
        'date': date
    }
    
    gallery_ref = db.reference('gallery')
    gallery_ref.push(image_data)
    
    return redirect('/admin_gallery')

@app.route('/admin_gallery/edit/<item_id>', methods=['GET', 'POST'])
def edit_gallery_item(item_id):
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    gallery_ref = db.reference(f'gallery/{item_id}')
    item = gallery_ref.get()
    
    if request.method == 'POST':
        title = request.form.get('title')
        
        if item.get('type') == 'video':
            video = request.files.get('video')
            
            item_data = {
                'title': title
            }
            
            if video:
                # Upload new video
                video_result = cloudinary.uploader.upload(video,
                    folder="gallery/videos",
                    resource_type="video",
                    chunk_size=6000000,
                    eager=[
                        {'format': 'mp4', 'quality': 'auto'}
                    ]
                )
                video_url = video_result['secure_url']
                item_data['video_url'] = video_url
            
            gallery_ref.update(item_data)
        else:
            image = request.files.get('image')
            
            item_data = {
                'title': title
            }
            
            if image:
                # Upload new image
                result = cloudinary.uploader.upload(image,
                    folder="gallery",
                    resource_type="image",
                    transformation=[
                        {'width': 1000, 'crop': "scale"},
                        {'quality': "auto"}
                    ]
                )
                item_data['url'] = result['secure_url']
            
            gallery_ref.update(item_data)
        
        return redirect('/admin_gallery')
    
    if item:
        item['id'] = item_id
        if item.get('type') == 'video':
            return render_template('admin_gallery_edit_video.html', item=item)
        else:
            return render_template('admin_gallery_edit.html', item=item)
    
    return redirect('/admin_gallery')

@app.route('/admin_gallery/delete/<item_id>', methods=['DELETE'])
def delete_gallery_item(item_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    gallery_ref = db.reference(f'gallery/{item_id}')
    item = gallery_ref.get()
    
    if item:
        # Delete from Cloudinary
        if item.get('type') == 'video':
            # Delete video
            video_url = item.get('video_url')
            if video_url:
                url_parts = video_url.split('/')
                public_id = '/'.join(url_parts[url_parts.index('upload')+1:]).split('.')[0]
                cloudinary.uploader.destroy(public_id, resource_type="video")
            
            # Delete thumbnail
            thumbnail_url = item.get('thumbnail_url')
            if thumbnail_url:
                url_parts = thumbnail_url.split('/')
                public_id = '/'.join(url_parts[url_parts.index('upload')+1:]).split('.')[0]
                cloudinary.uploader.destroy(public_id)
        else:
            # Delete image
            image_url = item.get('url')
            if image_url:
                url_parts = image_url.split('/')
                public_id = '/'.join(url_parts[url_parts.index('upload')+1:]).split('.')[0]
                cloudinary.uploader.destroy(public_id)
    
    # Delete from database
    gallery_ref.delete()
    
    return jsonify({'success': True})

@app.route('/admin_gallery/add_video', methods=['POST'])
def add_gallery_video():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    title = request.form.get('title')
    video = request.files.get('video')
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if video:
        # Upload video to Cloudinary
        video_result = cloudinary.uploader.upload(video,
            folder="gallery/videos",
            resource_type="video",
            chunk_size=6000000,  # 6MB chunks for large videos
            eager=[
                {'format': 'mp4', 'quality': 'auto'}
            ]
        )
        video_url = video_result['secure_url']
        
        video_data = {
            'title': title,
            'video_url': video_url,
            'date': date,
            'type': 'video'
        }
        
        gallery_ref = db.reference('gallery')
        gallery_ref.push(video_data)
    
    return redirect('/admin_gallery')

# Research Management
@app.route('/admin_research')
def admin_research():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    projects_ref = db.reference('research/projects')
    publications_ref = db.reference('research/publications')
    
    projects = projects_ref.get()
    publications = publications_ref.get()
    
    projects_list = []
    publications_list = []
    
    if projects:
        for key, project in projects.items():
            project['id'] = key
            projects_list.append(project)
        # Sort projects by date in descending order
        projects_list.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    if publications:
        for key, publication in publications.items():
            publication['id'] = key
            publications_list.append(publication)
        # Sort publications by date in descending order
        publications_list.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return render_template('admin_research.html', 
                         projects=projects_list,
                         publications=publications_list)

@app.route('/admin_research/add_project', methods=['POST'])
def add_research_project():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    title = request.form.get('title')
    description = request.form.get('description')
    creator_name = request.form.get('creator_name')
    status = request.form.get('status')
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Initialize related media list
    related_media = []
    
    # Handle main image upload
    image = request.files.get('image')
    if image:
        result = cloudinary.uploader.upload(image,
            folder="research/projects",
            resource_type="image",
            transformation=[
                {'width': 800, 'crop': "scale"},
                {'quality': "auto"}
            ]
        )
        image_url = result['secure_url']
    else:
        return redirect('/admin_research')  # Redirect if no main image provided
    
    # Handle related images
    related_images = request.files.getlist('related_images[]')
    for img in related_images:
        if img.filename:
            result = cloudinary.uploader.upload(img,
                folder="research/projects/related",
                resource_type="image",
                transformation=[
                    {'width': 800, 'crop': "scale"},
                    {'quality': "auto"}
                ]
            )
            related_media.append({
                'type': 'image',
                'url': result['secure_url'],
                'id': str(datetime.now().timestamp())
            })
    
    # Handle related videos
    related_videos = request.files.getlist('related_videos[]')
    for video in related_videos:
        if video.filename:
            result = cloudinary.uploader.upload(video,
                folder="research/projects/related",
                resource_type="video",
                chunk_size=6000000,
                eager=[
                    {'format': 'mp4', 'quality': 'auto'}
                ]
            )
            related_media.append({
                'type': 'video',
                'url': result['secure_url'],
                'id': str(datetime.now().timestamp())
            })
    
    project_data = {
        'title': title,
        'description': description,
        'creator_name': creator_name,
        'status': status,
        'date': date,
        'image_url': image_url,
        'related_media': related_media
    }
    
    projects_ref = db.reference('research/projects')
    projects_ref.push(project_data)
    
    return redirect('/admin_research')

@app.route('/admin_research/add_publication', methods=['POST'])
def add_research_publication():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    title = request.form.get('title')
    authors = request.form.get('authors')
    type = request.form.get('type')
    link = request.form.get('link')
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    publication_data = {
        'title': title,
        'authors': authors,
        'type': type,
        'link': link,
        'date': date
    }
    
    publications_ref = db.reference('research/publications')
    publications_ref.push(publication_data)
    
    return redirect('/admin_research')

@app.route('/admin_research/edit_publication/<publication_id>', methods=['GET', 'POST'])
def edit_publication(publication_id):
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    publications_ref = db.reference(f'research/publications/{publication_id}')
    
    if request.method == 'POST':
        title = request.form.get('title')
        authors = request.form.get('authors')
        type = request.form.get('type')
        link = request.form.get('link')
        
        publication_data = {
            'title': title,
            'authors': authors,
            'type': type,
            'link': link
        }
        
        publications_ref.update(publication_data)
        return redirect('/admin_research')
    
    publication = publications_ref.get()
    if publication:
        publication['id'] = publication_id
        return render_template('admin_research_edit.html', publication=publication)
    
    return redirect('/admin_research')

@app.route('/admin_research/delete_publication/<publication_id>', methods=['DELETE'])
def delete_publication(publication_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    publications_ref = db.reference(f'research/publications/{publication_id}')
    publications_ref.delete()
    
    return jsonify({'success': True})

@app.route('/admin_research/edit_project/<project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    projects_ref = db.reference(f'research/projects/{project_id}')
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        creator_name = request.form.get('creator_name')
        image = request.files.get('image')
        
        # Get existing project data
        existing_project = projects_ref.get()
        related_media = existing_project.get('related_media', [])
        
        project_data = {
            'title': title,
            'description': description,
            'creator_name': creator_name,
            'related_media': related_media
        }
        
        if image:
            # Upload new main image to Cloudinary
            result = cloudinary.uploader.upload(image,
                folder="research/projects",
                resource_type="image",
                transformation=[
                    {'width': 800, 'crop': "scale"},
                    {'quality': "auto"}
                ]
            )
            project_data['image_url'] = result['secure_url']
        
        # Handle related media uploads
        related_images = request.files.getlist('related_images[]')
        for img in related_images:
            if img.filename:
                result = cloudinary.uploader.upload(img,
                    folder="research/projects/related",
                    resource_type="image",
                    transformation=[
                        {'width': 800, 'crop': "scale"},
                        {'quality': "auto"}
                    ]
                )
                media_id = str(datetime.now().timestamp())
                related_media.append({
                    'type': 'image',
                    'url': result['secure_url'],
                    'id': media_id
                })
        
        # Upload related videos if provided
        related_videos = request.files.getlist('related_videos[]')
        for video in related_videos:
            if video.filename:
                result = cloudinary.uploader.upload(video,
                    folder="research/projects/related",
                    resource_type="video",
                    chunk_size=6000000,
                    eager=[
                        {'format': 'mp4', 'quality': 'auto'}
                    ]
                )
                media_id = str(datetime.now().timestamp())
                related_media.append({
                    'type': 'video',
                    'url': result['secure_url'],
                    'id': media_id
                })
        
        # Update the project data with new related media
        project_data['related_media'] = related_media
        
        projects_ref.update(project_data)
        return redirect('/admin_research')
    
    project = projects_ref.get()
    if project:
        project['id'] = project_id
        return render_template('admin_research_edit_project.html', project=project)
    
    return redirect('/admin_research')

@app.route('/admin_research/delete_project/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    projects_ref = db.reference(f'research/projects/{project_id}')
    projects_ref.delete()
    
    return jsonify({'success': True})

@app.route('/admin_research/delete_project_media/<media_id>', methods=['DELETE'])
def delete_project_media(media_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Get all projects
    projects_ref = db.reference('research/projects')
    projects = projects_ref.get()
    
    if projects:
        for project_id, project in projects.items():
            related_media = project.get('related_media', [])
            # Find and remove the media with matching ID
            for i, media in enumerate(related_media):
                if media.get('id') == media_id:
                    # Delete from Cloudinary
                    url = media.get('url')
                    if url:
                        url_parts = url.split('/')
                        public_id = '/'.join(url_parts[url_parts.index('upload')+1:]).split('.')[0]
                        cloudinary.uploader.destroy(public_id, resource_type="video" if media.get('type') == 'video' else "image")
                    
                    # Remove from array
                    related_media.pop(i)
                    # Update project in database
                    projects_ref.child(project_id).update({'related_media': related_media})
                    return jsonify({'success': True})
    
    return jsonify({'error': 'Media not found'}), 404

# Team Management
@app.route('/admin_team')
def admin_team():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    # Get team leads
    team_leads_ref = db.reference('team_leads')
    team_leads = team_leads_ref.get()
    if team_leads:
        team_leads = [{'id': k, **v} for k, v in team_leads.items()]
        team_leads.sort(key=lambda x: x.get('order', 0))
    else:
        team_leads = []
    
    # Get faculty members
    faculty_ref = db.reference('faculty')
    faculty_members = faculty_ref.get()
    if faculty_members:
        faculty_members = [{'id': k, **v} for k, v in faculty_members.items()]
        faculty_members.sort(key=lambda x: x.get('order', 0))
    else:
        faculty_members = []
    
    # Get team members
    team_ref = db.reference('team')
    team_members = team_ref.get()
    if team_members:
        team_members = [{'id': k, **v} for k, v in team_members.items()]
        team_members.sort(key=lambda x: x.get('order', 0))
    else:
        team_members = []
    
    # Get pass-out members
    passout_ref = db.reference('passout_members')
    passout_members = passout_ref.get()
    if passout_members:
        passout_members = [{'id': k, **v} for k, v in passout_members.items()]
        passout_members.sort(key=lambda x: x.get('passout_year', 0), reverse=True)
    else:
        passout_members = []
    
    return render_template('admin_team.html',
                         team_leads=team_leads,
                         faculty_members=faculty_members,
                         team_members=team_members,
                         passout_members=passout_members)

@app.route('/admin_team/add', methods=['POST'])
def add_team_member():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    name = request.form.get('name')
    role = request.form.get('role')
    
    email = request.form.get('email')
    linkedin = request.form.get('linkedin')

    image = request.files.get('image')
    order = int(request.form.get('order', 0))
    
    if image:
        # Upload image to Cloudinary
        result = cloudinary.uploader.upload(image,
            folder="team",  # Images will be stored in a 'team' folder
            resource_type="image",
            transformation=[
                {'width': 400, 'height': 400, 'crop': "fill"},
                {'quality': "auto"}
            ]
        )
        image_url = result['secure_url']
    else:
        image_url = None
    
    member_data = {
        'name': name,
        'role': role,
        'email': email,
        'linkedin': linkedin,

        'image_url': image_url,
        'order': order
    }
    
    team_ref = db.reference('team')
    team_ref.push(member_data)
    
    return redirect('/admin_team')

@app.route('/admin_team/edit/<member_id>', methods=['GET', 'POST'])
def edit_team_member(member_id):
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    team_ref = db.reference(f'team/{member_id}')
    
    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        email = request.form.get('email')
        linkedin = request.form.get('linkedin')
        image = request.files.get('image')
        order = int(request.form.get('order', 0))
        
        member_data = {
            'name': name,
            'role': role,

            'email': email,
            'linkedin': linkedin,

            'order': order
        }
        
        if image:
            # Upload new image to Cloudinary
            result = cloudinary.uploader.upload(image,
                folder="team",
                resource_type="image",
                transformation=[
                    {'width': 400, 'height': 400, 'crop': "fill"},
                    {'quality': "auto"}
                ]
            )
            member_data['image_url'] = result['secure_url']
        
        team_ref.update(member_data)
        return redirect('/admin_team')
    
    member = team_ref.get()
    if member:
        member['id'] = member_id
        return render_template('admin_team_edit.html', member=member)
    
    return redirect('/admin_team')

@app.route('/admin_team/delete/<member_id>', methods=['DELETE'])
def delete_team_member(member_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    team_ref = db.reference(f'team/{member_id}')
    team_ref.delete()
    
    return jsonify({'success': True})

@app.route('/admin_team/add_lead', methods=['POST'])
def add_team_lead():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    name = request.form.get('name')
    role = request.form.get('role')
    department = request.form.get('department')
    linkedin = request.form.get('linkedin')
    order = int(request.form.get('order', 0))
    
    if 'image' not in request.files:
        flash('No image file provided', 'error')
        return redirect(url_for('admin_team'))
    
    image = request.files['image']
    if image.filename == '':
        flash('No image selected', 'error')
        return redirect(url_for('admin_team'))
    
    try:
        # Upload image to Cloudinary
        result = cloudinary.uploader.upload(image)
        image_url = result['secure_url']
        
        # Save team lead data to Firebase
        team_leads_ref = db.reference('team_leads')
        new_lead = {
            'name': name,
            'role': role,
            'department': department,
            'linkedin': linkedin,
            'image_url': image_url,
            'order': order
        }
        team_leads_ref.push(new_lead)
        
        flash('Team lead added successfully', 'success')
    except Exception as e:
        flash(f'Error adding team lead: {str(e)}', 'error')
    
    return redirect(url_for('admin_team'))

@app.route('/admin_team/update_lead', methods=['POST'])
def update_team_lead():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    lead_id = request.form.get('lead_id')
    name = request.form.get('name')
    role = request.form.get('role')
    department = request.form.get('department')
    linkedin = request.form.get('linkedin')
    order = int(request.form.get('order', 0))
    
    try:
        team_leads_ref = db.reference(f'team_leads/{lead_id}')
        current_lead = team_leads_ref.get()
        
        if not current_lead:
            flash('Team lead not found', 'error')
            return redirect(url_for('admin_team'))
        
        lead_data = {
            'name': name,
            'role': role,
            'department': department,
            'linkedin': linkedin,
            'order': order
        }
        
        # Handle image upload if a new image is provided
        if 'image' in request.files and request.files['image'].filename != '':
            image = request.files['image']
            result = cloudinary.uploader.upload(image)
            lead_data['image_url'] = result['secure_url']
            
            # Delete old image from Cloudinary if it exists
            if current_lead.get('image_url'):
                public_id = current_lead['image_url'].split('/')[-1].split('.')[0]
                cloudinary.uploader.destroy(public_id)
        
        team_leads_ref.update(lead_data)
        flash('Team lead updated successfully', 'success')
    except Exception as e:
        flash(f'Error updating team lead: {str(e)}', 'error')
    
    return redirect(url_for('admin_team'))

@app.route('/admin_team/delete_lead/<lead_id>', methods=['POST'])
def delete_team_lead(lead_id):
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    team_leads_ref = db.reference(f'team_leads/{lead_id}')
    team_leads_ref.delete()
    
    return redirect('/admin_team')

# Faculty/PI Management Routes
@app.route('/admin_faculty')
def admin_faculty():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    faculty_ref = db.reference('faculty')
    faculty = faculty_ref.get()
    faculty_list = []
    
    if faculty:
        for key, member in faculty.items():
            member['id'] = key
            faculty_list.append(member)
        # Sort faculty by order
        faculty_list.sort(key=lambda x: x.get('order', 0))
    
    return render_template('admin_faculty.html', faculty_members=faculty_list)

@app.route('/admin_faculty/add', methods=['POST'])
def add_faculty_member():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    name = request.form.get('name')
    role = request.form.get('role')
    department = request.form.get('department')
    email = request.form.get('email')
    linkedin = request.form.get('linkedin')

    order = int(request.form.get('order', 0))
    
    # Handle image upload
    image_url = ''
    if 'image' in request.files:
        image = request.files['image']
        if image.filename != '':
            try:
                upload_result = cloudinary.uploader.upload(image)
                image_url = upload_result['secure_url']
            except Exception as e:
                flash('Error uploading image: ' + str(e))
                return redirect('/admin_faculty')
    
    faculty_data = {
        'name': name,
        'role': role,
        'department' : department,
        'email': email,
        'linkedin': linkedin,

        'image_url': image_url,
        'order': order
    }
    
    faculty_ref = db.reference('faculty')
    faculty_ref.push(faculty_data)
    
    return redirect('/admin_faculty')

@app.route('/admin_faculty/edit/<member_id>', methods=['GET', 'POST'])
def edit_faculty_member(member_id):
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    faculty_ref = db.reference(f'faculty/{member_id}')
    
    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        department = request.form.get('department')
        email = request.form.get('email')
        linkedin = request.form.get('linkedin')

        order = int(request.form.get('order', 0))
        
        faculty_data = {
            'name': name,
            'role': role,
            'department' : department,
            'email': email,
            'linkedin': linkedin,
            'order': order
        }
        
        # Handle image upload if new image is provided
        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '':
                try:
                    upload_result = cloudinary.uploader.upload(image)
                    faculty_data['image_url'] = upload_result['secure_url']
                except Exception as e:
                    flash('Error uploading image: ' + str(e))
                    return redirect('/admin_faculty')
        
        faculty_ref.update(faculty_data)
        return redirect('/admin_faculty')
    
    member = faculty_ref.get()
    if member:
        member['id'] = member_id
        return render_template('admin_faculty_edit.html', member=member)
    
    return redirect('/admin_faculty')

@app.route('/admin_faculty/delete/<member_id>', methods=['DELETE'])
def delete_faculty_member(member_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    faculty_ref = db.reference(f'faculty/{member_id}')
    faculty_ref.delete()
    
    return jsonify({'success': True})

# About Management
@app.route('/admin_about')
def admin_about():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    about_ref = db.reference('about')
    about = about_ref.get()
    
    return render_template('admin_about.html', about=about)

@app.route('/admin_about/update', methods=['POST'])
def update_about():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    # Get statistics values
    team_members = int(request.form.get('team_members', 0))
    active_projects = int(request.form.get('active_projects', 0))
    trained_interns = int(request.form.get('trained_interns', 0))
    publications = int(request.form.get('publications', 0))

    # Get welcome text
    welcome_title = request.form.get('welcome_title')
    welcome_content = request.form.get('welcome_content')
    
    # Get facilities data
    facilities = []
    facility_titles = request.form.getlist('facility_title[]')
    facility_descriptions = request.form.getlist('facility_description[]')
    facility_icons = request.form.getlist('facility_icon[]')
    
    for i in range(len(facility_titles)):
        if facility_titles[i] and facility_descriptions[i]:
            facilities.append({
                'title': facility_titles[i],
                'description': facility_descriptions[i],
                'icon': facility_icons[i]
            })
    
    about_data = {
        'team_members': team_members,
        'active_projects': active_projects,
        'trained_interns': trained_interns,
        'publications': publications,
        'welcome_text': {
            'title': welcome_title,
            'content': welcome_content
        },
        'facilities': facilities
    }
    
    about_ref = db.reference('about')
    about_ref.update(about_data)
    
    return redirect('/admin_about')

@app.route('/admin_home')
def admin_home():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    slides_ref = db.reference('home/slides')
    drones_ref = db.reference('home/drones')
    
    slides = slides_ref.get()
    drones = drones_ref.get()
    
    slides_list = []
    drones_list = []
    
    if slides:
        for key, slide in slides.items():
            slide['id'] = key
            slides_list.append(slide)
        # Sort slides by order
        slides_list.sort(key=lambda x: x.get('order', 0))
    
    if drones:
        for key, drone in drones.items():
            drone['id'] = key
            drones_list.append(drone)
    
    return render_template('admin_home.html', slides=slides_list, drones=drones_list)

@app.route('/admin_home/add_slide', methods=['POST'])
def add_slide():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    image = request.files.get('image')
    order = int(request.form.get('order', 0))
    
    if image:
        # Upload image to Cloudinary
        result = cloudinary.uploader.upload(image,
            folder="home/slides",
            resource_type="image",
            transformation=[
                {'width': 1920, 'crop': "scale"},
                {'quality': "auto"}
            ]
        )
        image_url = result['secure_url']
        
        slide_data = {
            'image_url': image_url,
            'order': order
        }
        
        slides_ref = db.reference('home/slides')
        slides_ref.push(slide_data)
    
    return redirect('/admin_home')

@app.route('/admin_home/edit_slide/<slide_id>', methods=['GET', 'POST'])
def edit_slide(slide_id):
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    slides_ref = db.reference(f'home/slides/{slide_id}')
    
    if request.method == 'POST':
        image = request.files.get('image')
        order = int(request.form.get('order', 0))
        
        slide_data = {
            'order': order
        }
        
        if image:
            # Upload new image to Cloudinary
            result = cloudinary.uploader.upload(image,
                folder="home/slides",
                resource_type="image",
                transformation=[
                    {'width': 1920, 'crop': "scale"},
                    {'quality': "auto"}
                ]
            )
            slide_data['image_url'] = result['secure_url']
        
        slides_ref.update(slide_data)
        return redirect('/admin_home')
    
    slide = slides_ref.get()
    if slide:
        slide['id'] = slide_id
        return render_template('admin_home_edit_slide.html', slide=slide)
    
    return redirect('/admin_home')

@app.route('/admin_home/delete_slide/<slide_id>', methods=['DELETE'])
def delete_slide(slide_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    slides_ref = db.reference(f'home/slides/{slide_id}')
    slide = slides_ref.get()
    
    if slide:
        # Delete image from Cloudinary
        image_url = slide.get('image_url')
        if image_url:
            url_parts = image_url.split('/')
            public_id = '/'.join(url_parts[url_parts.index('upload')+1:]).split('.')[0]
            cloudinary.uploader.destroy(public_id)
    
    slides_ref.delete()
    return jsonify({'success': True})

@app.route('/admin_home/add_drone', methods=['POST'])
def add_drone():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    image = request.files.get('image')
    title = request.form.get('title')
    description = request.form.get('description')
    creator_name = request.form.get('creator_name')
    
    if image:
        # Upload main image to Cloudinary
        result = cloudinary.uploader.upload(image,
            folder="home/drones",
            resource_type="image",
            transformation=[
                {'width': 800, 'crop': "scale"},
                {'quality': "auto"}
            ]
        )
        image_url = result['secure_url']
        
        # Handle related media uploads
        related_media = []
        
        # Upload related images if provided
        related_images = request.files.getlist('related_images[]')
        for img in related_images:
            if img.filename:
                result = cloudinary.uploader.upload(img,
                    folder="home/drones/related",
                    resource_type="image",
                    transformation=[
                        {'width': 800, 'crop': "scale"},
                        {'quality': "auto"}
                    ]
                )
                media_id = str(datetime.now().timestamp())
                related_media.append({
                    'type': 'image',
                    'url': result['secure_url'],
                    'id': media_id
                })
        
        # Upload related videos if provided
        related_videos = request.files.getlist('related_videos[]')
        for video in related_videos:
            if video.filename:
                result = cloudinary.uploader.upload(video,
                    folder="home/drones/related",
                    resource_type="video",
                    chunk_size=6000000,
                    eager=[
                        {'format': 'mp4', 'quality': 'auto'}
                    ]
                )
                media_id = str(datetime.now().timestamp())
                related_media.append({
                    'type': 'video',
                    'url': result['secure_url'],
                    'id': media_id
                })
        
        drone_data = {
            'image_url': image_url,
            'title': title,
            'description': description,
            'creator_name': creator_name,
            'related_media': related_media
        }
        
        drones_ref = db.reference('home/drones')
        drones_ref.push(drone_data)
    
    return redirect('/admin_home')

@app.route('/admin_home/edit_drone/<drone_id>', methods=['GET', 'POST'])
def edit_drone(drone_id):
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    drones_ref = db.reference(f'home/drones/{drone_id}')
    
    if request.method == 'POST':
        image = request.files.get('image')
        title = request.form.get('title')
        description = request.form.get('description')
        
        # Get existing drone data
        existing_drone = drones_ref.get()
        related_media = existing_drone.get('related_media', [])
        
        # Ensure all existing media items have IDs
        for media in related_media:
            if not media.get('id'):
                media['id'] = str(datetime.now().timestamp())
        
        drone_data = {
            'title': title,
            'description': description,
            'related_media': related_media
        }
        
        if image:
            # Upload new main image to Cloudinary
            result = cloudinary.uploader.upload(image,
                folder="home/drones",
                resource_type="image",
                transformation=[
                    {'width': 800, 'crop': "scale"},
                    {'quality': "auto"}
                ]
            )
            drone_data['image_url'] = result['secure_url']
        
        # Handle related media uploads
        related_images = request.files.getlist('related_images[]')
        for img in related_images:
            if img.filename:
                result = cloudinary.uploader.upload(img,
                    folder="home/drones/related",
                    resource_type="image",
                    transformation=[
                        {'width': 800, 'crop': "scale"},
                        {'quality': "auto"}
                    ]
                )
                media_id = str(datetime.now().timestamp())
                related_media.append({
                    'type': 'image',
                    'url': result['secure_url'],
                    'id': media_id
                })
        
        # Update the drone data with new related media
        drone_data['related_media'] = related_media
        
        # Update the drone in the database
        drones_ref.update(drone_data)
        return redirect('/admin_home')
    
    drone = drones_ref.get()
    if drone:
        # Ensure all existing media items have IDs
        if 'related_media' in drone:
            for media in drone['related_media']:
                if not media.get('id'):
                    media['id'] = str(datetime.now().timestamp())
            # Update the drone with the new IDs
            drones_ref.update({'related_media': drone['related_media']})
        
        drone['id'] = drone_id
        return render_template('admin_home_edit_drone.html', drone=drone)
    
    return redirect('/admin_home')

@app.route('/admin_home/delete_drone/<drone_id>', methods=['DELETE'])
def delete_drone(drone_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    drones_ref = db.reference(f'home/drones/{drone_id}')
    drone = drones_ref.get()
    
    if drone:
        # Delete image from Cloudinary
        image_url = drone.get('image_url')
        if image_url:
            url_parts = image_url.split('/')
            public_id = '/'.join(url_parts[url_parts.index('upload')+1:]).split('.')[0]
            cloudinary.uploader.destroy(public_id)
    
    drones_ref.delete()
    return jsonify({'success': True})

@app.route('/admin_home/delete_related_media/<drone_id>/<media_id>', methods=['DELETE'])
def delete_related_media(drone_id, media_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        print(f"Attempting to delete media with ID: {media_id} from drone: {drone_id}")
        
        # Get the specific drone
        drones_ref = db.reference(f'home/drones/{drone_id}')
        drone = drones_ref.get()
        
        if not drone:
            print(f"Drone {drone_id} not found")
            return jsonify({'error': 'Drone not found'}), 404
        
        related_media = drone.get('related_media', [])
        print(f"Found {len(related_media)} related media items")
        
        # Find and remove the media with matching ID
        for i, media in enumerate(related_media):
            media_id_str = str(media.get('id', ''))
            target_id_str = str(media_id)
            print(f"Checking media item {i}: {media_id_str} vs {target_id_str}")
            if media_id_str == target_id_str:
                try:
                    # Delete from Cloudinary
                    url = media.get('url')
                    if url:
                        print(f"Deleting from Cloudinary: {url}")
                        url_parts = url.split('/')
                        public_id = '/'.join(url_parts[url_parts.index('upload')+1:]).split('.')[0]
                        cloudinary.uploader.destroy(public_id, resource_type="video" if media.get('type') == 'video' else "image")
                    
                    # Remove from array
                    related_media.pop(i)
                    print(f"Removed media item {i} from array")
                    
                    # Update drone in database
                    print(f"Updating drone {drone_id} in database")
                    drones_ref.update({'related_media': related_media})
                    return jsonify({'success': True})
                except Exception as e:
                    print(f"Error deleting media: {str(e)}")
                    return jsonify({'error': f'Error deleting media: {str(e)}'}), 500
        
        print(f"Media with ID {media_id} not found in drone {drone_id}")
        return jsonify({'error': 'Media not found'}), 404
    except Exception as e:
        print(f"Error in delete_related_media: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/admin_messages/delete_message/<message_id>', methods=['POST'])
def delete_message(message_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_login'))
    
    try:
        # Get reference to the specific message
        message_ref = db.reference(f'messages/{message_id}')
        # Delete the message
        message_ref.delete()
        flash('Message deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting message: {str(e)}', 'error')
    
    return redirect(url_for('admin_messages'))

@app.route('/admin_team/get_lead/<lead_id>')
def get_team_lead(lead_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    try:
        team_leads_ref = db.reference(f'team_leads/{lead_id}')
        lead_data = team_leads_ref.get()
        
        if lead_data:
            return jsonify({
                'success': True,
                'lead': lead_data
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Team lead not found'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/drone/<drone_id>')
def drone_details(drone_id):
    # Get drone details from Firebase
    drone_ref = db.reference(f'home/drones/{drone_id}')
    drone = drone_ref.get()
    
    if not drone:
        return redirect(url_for('index'))
    
    # Get related media (images and videos) from gallery
    gallery_ref = db.reference('gallery')
    gallery_items = gallery_ref.get()
    related_media = []
    
    if gallery_items:
        for key, item in gallery_items.items():
            # Add items that are related to this drone
            if item.get('drone_id') == drone_id:
                item['id'] = key
                related_media.append(item)
    
    return render_template('drone_details.html', drone=drone, related_media=related_media)

@app.route('/project/<project_id>')
def project_details(project_id):
    # Get project details from Firebase
    project_ref = db.reference(f'research/projects/{project_id}')
    project = project_ref.get()
    
    if not project:
        return redirect(url_for('research'))
    
    # Get related media from the project's related_media field
    related_media = project.get('related_media', [])
    
    return render_template('project_details.html', project=project, related_media=related_media)

@app.route('/admin_team/add_passout', methods=['POST'])
def add_passout_member():
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    name = request.form.get('name')
    role = request.form.get('role')

    email = request.form.get('email')
    linkedin = request.form.get('linkedin')

    passout_year = request.form.get('passout_year')

    image = request.files.get('image')
    
    if image:
        # Upload image to Cloudinary
        result = cloudinary.uploader.upload(image,
            folder="team/passout",
            resource_type="image",
            transformation=[
                {'width': 400, 'height': 400, 'crop': "fill"},
                {'quality': "auto"}
            ]
        )
        image_url = result['secure_url']
    else:
        image_url = None
    
    member_data = {
        'name': name,
        'role': role,

        'email': email,
        'linkedin': linkedin,

        'image_url': image_url,
        'passout_year': passout_year,

    }
    
    passout_ref = db.reference('passout_members')
    passout_ref.push(member_data)
    
    return redirect('/admin_team')

@app.route('/admin_team/edit_passout/<member_id>', methods=['GET', 'POST'])
def edit_passout_member(member_id):
    if 'user_id' not in session:
        return redirect('/admin_login')
    
    passout_ref = db.reference(f'passout_members/{member_id}')
    
    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')

        email = request.form.get('email')
        linkedin = request.form.get('linkedin')

        passout_year = request.form.get('passout_year')

        image = request.files.get('image')
        
        member_data = {
            'name': name,
            'role': role,

            'email': email,
            'linkedin': linkedin,

            'passout_year': passout_year,
        }
        
        if image:
            # Upload new image to Cloudinary
            result = cloudinary.uploader.upload(image,
                folder="team/passout",
                resource_type="image",
                transformation=[
                    {'width': 400, 'height': 400, 'crop': "fill"},
                    {'quality': "auto"}
                ]
            )
            member_data['image_url'] = result['secure_url']
        
        passout_ref.update(member_data)
        return redirect('/admin_team')
    
    member = passout_ref.get()
    if member:
        member['id'] = member_id
        return render_template('admin_team_edit_passout.html', member=member)
    
    return redirect('/admin_team')

@app.route('/admin_team/delete_passout/<member_id>', methods=['DELETE'])
def delete_passout_member(member_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    passout_ref = db.reference(f'passout_members/{member_id}')
    passout_ref.delete()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)
